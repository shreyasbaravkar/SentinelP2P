import pandas as pd

# Load all CSVs
emp = pd.read_csv("employees.csv")
ven = pd.read_csv("vendors.csv")
po = pd.read_csv("purchase_orders.csv")
inv = pd.read_csv("invoices.csv")
con = pd.read_csv("contracts.csv")

print(f"Loaded: {len(emp)} employees, {len(ven)} vendors, {len(po)} POs, {len(inv)} invoices, {len(con)} contracts")

# ============================================================
# BUILD WEAK LABELS FOR INVOICES
# An invoice is "risky" (label=1) if flagged by any invoice-level rule
# ============================================================

# risky_invoice_ids = set()

# # Rule: duplicate invoice (same po_id, same amount)
# dup_inv = inv[inv.duplicated(["po_id", "amount"], keep=False)]
# risky_invoice_ids.update(dup_inv["invoice_id"])

# # Rule: invoice amount exceeds contract rate by 30%+
# inv_po = inv.merge(po[["po_id", "vendor_id"]], on="po_id")
# inv_con = inv_po.merge(con[["vendor_id", "agreed_rate"]], on="vendor_id")
# rate_mismatch = inv_con[inv_con["amount"] > inv_con["agreed_rate"] * 1.3]
# risky_invoice_ids.update(rate_mismatch["invoice_id"])

# # Rule: PO category doesn't match invoice category
# po_inv_cat = po.merge(inv, on="po_id", suffixes=("_po", "_inv"))
# cat_mismatch = po_inv_cat[po_inv_cat["item_category_po"] != po_inv_cat["item_category_inv"]]
# risky_invoice_ids.update(cat_mismatch["invoice_id"])

# # Add the label column to the invoices dataframe
# inv["is_risky"] = inv["invoice_id"].isin(risky_invoice_ids).astype(int)

# print(f"Total invoices flagged as risky (weak label): {inv['is_risky'].sum()} out of {len(inv)}")


# ============================================================
# TRAINING LABELS — deliberately HIDING the contract-rate rule
# so we can test if the GNN can catch it WITHOUT being told about it
# ============================================================

visible_risky_ids = set()   # what the GNN IS trained on
hidden_risky_ids = set()    # what the GNN is NOT told about (our test)

# Rule: duplicate invoice (VISIBLE — GNN trains on this)
dup_inv = inv[inv.duplicated(["po_id", "amount"], keep=False)]
visible_risky_ids.update(dup_inv["invoice_id"])

# Rule: PO category doesn't match invoice category (VISIBLE — GNN trains on this)
po_inv_cat = po.merge(inv, on="po_id", suffixes=("_po", "_inv"))
cat_mismatch = po_inv_cat[po_inv_cat["item_category_po"] != po_inv_cat["item_category_inv"]]
visible_risky_ids.update(cat_mismatch["invoice_id"])

# Rule: invoice amount exceeds contract rate by 30%+ (HIDDEN — GNN never told)
inv_po = inv.merge(po[["po_id", "vendor_id"]], on="po_id")
inv_con = inv_po.merge(con[["vendor_id", "agreed_rate"]], on="vendor_id")
rate_mismatch = inv_con[inv_con["amount"] > inv_con["agreed_rate"] * 1.3]
hidden_risky_ids.update(rate_mismatch["invoice_id"])

# Isolate invoices flagged ONLY by the hidden rule (clean test group —
# not already "given away" by one of the visible rules)
hidden_only_ids = hidden_risky_ids - visible_risky_ids

# Training label uses ONLY the visible rules
inv["is_risky"] = inv["invoice_id"].isin(visible_risky_ids).astype(int)

# Separate column marking the hidden-only test group (NOT used in training)
inv["hidden_test_case"] = inv["invoice_id"].isin(hidden_only_ids).astype(int)

print(f"Visible risky (used for training): {inv['is_risky'].sum()} out of {len(inv)}")
print(f"Hidden-only test cases (NOT trained on): {inv['hidden_test_case'].sum()}")

from sklearn.preprocessing import LabelEncoder
import torch

# ============================================================
# ENCODE CATEGORICAL FEATURES INTO NUMBERS
# ============================================================

def encode_column(df, column):
    """Converts a text column into numbers (e.g. 'Finance' -> 0, 'IT' -> 1)"""
    le = LabelEncoder()
    return le.fit_transform(df[column].astype(str))

# ---------- Employee features ----------
emp["department_enc"] = encode_column(emp, "department")
emp["role_enc"] = encode_column(emp, "role")

employee_features = torch.tensor(
    emp[["department_enc", "role_enc"]].values, dtype=torch.float
)
print(f"Employee feature matrix shape: {employee_features.shape}")

# ---------- Vendor features ----------
ven["vendor_category_enc"] = encode_column(ven, "vendor_category")
ven["has_contract_enc"] = (ven["has_contract"] == "Yes").astype(int)

vendor_features = torch.tensor(
    ven[["vendor_category_enc", "has_contract_enc"]].values, dtype=torch.float
)
print(f"Vendor feature matrix shape: {vendor_features.shape}")

# ---------- Purchase Order features ----------
po["item_category_enc"] = encode_column(po, "item_category")
po["amount_norm"] = (po["amount"] - po["amount"].mean()) / po["amount"].std()

po_features = torch.tensor(
    po[["amount_norm", "item_category_enc"]].values, dtype=torch.float
)
print(f"PO feature matrix shape: {po_features.shape}")

# ---------- Invoice features ----------
inv["item_category_enc"] = encode_column(inv, "item_category")
inv["payment_status_enc"] = encode_column(inv, "payment_status")
inv["amount_norm"] = (inv["amount"] - inv["amount"].mean()) / inv["amount"].std()

invoice_features = torch.tensor(
    inv[["amount_norm", "item_category_enc", "payment_status_enc"]].values, dtype=torch.float
)
invoice_labels = torch.tensor(inv["is_risky"].values, dtype=torch.long)
hidden_test_mask_full = torch.tensor(inv["hidden_test_case"].values, dtype=torch.bool)
print(f"Invoice feature matrix shape: {invoice_features.shape}")
print(f"Invoice labels shape: {invoice_labels.shape}")

from torch_geometric.data import HeteroData

# ---------- Contract features ----------
con["rate_norm"] = (con["agreed_rate"] - con["agreed_rate"].mean()) / con["agreed_rate"].std()

contract_features = torch.tensor(
    con[["rate_norm"]].values, dtype=torch.float
)
print(f"Contract feature matrix shape: {contract_features.shape}")

# ============================================================
# BUILD ID -> INDEX LOOKUPS
# (PyTorch Geometric needs plain numbers, not text IDs like "EMP001")
# ============================================================

emp_id_to_idx = {eid: i for i, eid in enumerate(emp["employee_id"])}
ven_id_to_idx = {vid: i for i, vid in enumerate(ven["vendor_id"])}
po_id_to_idx = {pid: i for i, pid in enumerate(po["po_id"])}
inv_id_to_idx = {iid: i for i, iid in enumerate(inv["invoice_id"])}
con_id_to_idx = {cid: i for i, cid in enumerate(con["contract_id"])}
# ============================================================
# BUILD EDGES
# ============================================================

# Employee -> CREATED -> Vendor
created_src = [emp_id_to_idx[e] for e in ven["created_by_employee_id"]]
created_dst = list(range(len(ven)))
created_edge_index = torch.tensor([created_src, created_dst], dtype=torch.long)

# Employee -> RAISED -> PurchaseOrder
raised_src = [emp_id_to_idx[e] for e in po["created_by_employee_id"]]
raised_dst = list(range(len(po)))
raised_edge_index = torch.tensor([raised_src, raised_dst], dtype=torch.long)

# Employee -> APPROVED -> PurchaseOrder
approved_src = [emp_id_to_idx[e] for e in po["approved_by_employee_id"]]
approved_dst = list(range(len(po)))
approved_edge_index = torch.tensor([approved_src, approved_dst], dtype=torch.long)

# Vendor -> RECEIVED -> PurchaseOrder
received_src = [ven_id_to_idx[v] for v in po["vendor_id"]]
received_dst = list(range(len(po)))
received_edge_index = torch.tensor([received_src, received_dst], dtype=torch.long)

# PurchaseOrder -> HAS_INVOICE -> Invoice
hasinv_src = [po_id_to_idx[p] for p in inv["po_id"]]
hasinv_dst = list(range(len(inv)))
hasinv_edge_index = torch.tensor([hasinv_src, hasinv_dst], dtype=torch.long)

# Vendor -> HAS_CONTRACT -> Contract
hascon_src = [ven_id_to_idx[v] for v in con["vendor_id"]]
hascon_dst = list(range(len(con)))
hascon_edge_index = torch.tensor([hascon_src, hascon_dst], dtype=torch.long)

print(f"  Vendor -HAS_CONTRACT-> Contract: {hascon_edge_index.shape[1]}")
print("Edges built:")
print(f"  Employee -CREATED-> Vendor: {created_edge_index.shape[1]}")
print(f"  Employee -RAISED-> PO: {raised_edge_index.shape[1]}")
print(f"  Employee -APPROVED-> PO: {approved_edge_index.shape[1]}")
print(f"  Vendor -RECEIVED-> PO: {received_edge_index.shape[1]}")
print(f"  PO -HAS_INVOICE-> Invoice: {hasinv_edge_index.shape[1]}")

# ============================================================
# ASSEMBLE THE HETEROGENEOUS GRAPH
# ============================================================

data = HeteroData()

# Node features
data["employee"].x = employee_features
data["vendor"].x = vendor_features
data["purchase_order"].x = po_features
data["invoice"].x = invoice_features
data["invoice"].y = invoice_labels
data["contract"].x = contract_features

# Edges
data["employee", "created", "vendor"].edge_index = created_edge_index
data["employee", "raised", "purchase_order"].edge_index = raised_edge_index
data["employee", "approved", "purchase_order"].edge_index = approved_edge_index
data["vendor", "received", "purchase_order"].edge_index = received_edge_index
data["purchase_order", "has_invoice", "invoice"].edge_index = hasinv_edge_index
data["vendor", "has_contract", "contract"].edge_index = hascon_edge_index

print()
print("Graph assembled:")
print(data)

import torch_geometric.transforms as T

data = T.ToUndirected()(data)
print()
print("After making undirected:")
print(data)

from sklearn.model_selection import train_test_split
import numpy as np

# ============================================================
# TRAIN / TEST SPLIT FOR INVOICES
# ============================================================

num_invoices = len(inv)
all_indices = np.arange(num_invoices)

train_idx, test_idx = train_test_split(
    all_indices,
    test_size=0.2,
    random_state=42,
    stratify=invoice_labels.numpy()
)

# Create boolean masks (True/False for every invoice)
train_mask = torch.zeros(num_invoices, dtype=torch.bool)
train_mask[train_idx] = True

test_mask = torch.zeros(num_invoices, dtype=torch.bool)
test_mask[test_idx] = True

data["invoice"].train_mask = train_mask
data["invoice"].test_mask = test_mask
data["invoice"].hidden_test_mask = hidden_test_mask_full
print(f"Train invoices: {train_mask.sum().item()}")
print(f"Test invoices: {test_mask.sum().item()}")
print(f"Risky invoices in train: {invoice_labels[train_mask].sum().item()}")
print(f"Risky invoices in test: {invoice_labels[test_mask].sum().item()}")

# ============================================================
# SAVE THE GRAPH TO DISK
# ============================================================

torch.save(data, "graph_data.pt")
print()
print("Graph saved to graph_data.pt")