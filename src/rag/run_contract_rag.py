import pandas as pd
import numpy as np
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

invoices = pd.read_csv("../../data/invoices.csv")
contracts = pd.read_csv("../../data/contracts.csv")
pos = pd.read_csv("../../data/purchase_orders.csv")
print(f"Loaded {len(invoices)} invoices, {len(pos)} purchase orders")

model = SentenceTransformer("all-MiniLM-L6-v2")
invoices = invoices.merge(pos[["po_id", "vendor_id"]], on="po_id", how="left")
contract_by_vendor = contracts.drop_duplicates(subset="vendor_id", keep="first").set_index("vendor_id")

print("Embedding invoice descriptions...")
desc_embeddings = model.encode(invoices["description"].tolist(), show_progress_bar=True)

results = []
for i, row in invoices.iterrows():
    vendor_id = row["vendor_id"]

    if pd.isna(vendor_id) or vendor_id not in contract_by_vendor.index:
        results.append({
            "invoice_id": row["invoice_id"],
            "vendor_id": vendor_id,
            "contract_text": None,
            "similarity": None,
            "rag_status": "no_contract_on_file",
        })
        continue

    contract_row = contract_by_vendor.loc[vendor_id]
    contract_vec = model.encode(contract_row["contract_text"])
    inv_vec = desc_embeddings[i]
    similarity = np.dot(inv_vec, contract_vec) / (
        np.linalg.norm(inv_vec) * np.linalg.norm(contract_vec)
    )

    results.append({
        "invoice_id": row["invoice_id"],
        "vendor_id": vendor_id,
        "contract_text": contract_row["contract_text"],
        "similarity": float(similarity),
        "rag_status": None,  # filled in after we pick a threshold
    })

results_df = pd.DataFrame(results)
results_df.to_csv("../../data/rag_similarity_scores.csv", index=False)

print(f"\nSaved {len(results_df)} rows to ../../data/rag_similarity_scores.csv")
print(f"no_contract_on_file: {(results_df['rag_status'] == 'no_contract_on_file').sum()}")
print(f"scored (has contract): {results_df['similarity'].notna().sum()}")
print()
print(results_df["similarity"].describe())
print()
print("Lowest 10 similarity scores (likely mismatches):")
print(results_df.dropna(subset=["similarity"]).nsmallest(10, "similarity")[["invoice_id", "vendor_id", "similarity"]])