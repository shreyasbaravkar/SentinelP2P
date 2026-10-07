import torch
import torch.nn.functional as F
from torch_geometric.nn import HeteroConv, SAGEConv, Linear
import pandas as pd 
# ============================================================
# LOAD THE SAVED GRAPH
# ============================================================

data = torch.load("../../data/graph_data.pt", weights_only=False)
print("Graph loaded:")
print(data)

# ============================================================
# DEFINE THE GNN MODEL
# ============================================================

class FraudGNN(torch.nn.Module):
    def __init__(self, hidden_channels, out_channels):
        super().__init__()

        # Layer 1: each node type learns from its direct neighbors
        self.conv1 = HeteroConv({
            edge_type: SAGEConv((-1, -1), hidden_channels)
            for edge_type in data.edge_types
        }, aggr="sum")
        # Layer 2: each node type learns from neighbors-of-neighbors
        self.conv2 = HeteroConv({
            edge_type: SAGEConv((-1, -1), hidden_channels)
            for edge_type in data.edge_types
        }, aggr="sum")

        # Layer 3: extends reach further (e.g. lets Contract info reach Invoice)
        self.conv3 = HeteroConv({
            edge_type: SAGEConv((-1, -1), hidden_channels)
            for edge_type in data.edge_types
        }, aggr="sum")

        #Final layer: turns invoice's learned representation into a risk score
        self.classifier = Linear(hidden_channels, out_channels)

       
    def forward(self, x_dict, edge_index_dict):
        x_dict = self.conv1(x_dict, edge_index_dict)
        x_dict = {key: F.relu(x) for key, x in x_dict.items()}

        x_dict = self.conv2(x_dict, edge_index_dict)
        x_dict = {key: F.relu(x) for key, x in x_dict.items()}

        x_dict = self.conv3(x_dict, edge_index_dict)
        x_dict = {key: F.relu(x) for key, x in x_dict.items()}

        # We only care about predicting risk for invoices
        out = self.classifier(x_dict["invoice"])
        return out

model = FraudGNN(hidden_channels=32, out_channels=2)
print()
print(model)

# ============================================================
# TRAINING SETUP
# ============================================================

optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

train_mask = data["invoice"].train_mask
test_mask = data["invoice"].test_mask
labels = data["invoice"].y

# ============================================================
# CALCULATE CLASS WEIGHTS (to fix class imbalance)
# ============================================================

train_labels = labels[train_mask]
num_not_risky = (train_labels == 0).sum().item()
num_risky = (train_labels == 1).sum().item()

# Give the minority class (risky) a proportionally higher weight
class_weights = torch.tensor([
    1.0,                              # weight for "not risky"
    num_not_risky / num_risky         # weight for "risky" — higher since it's rarer
], dtype=torch.float)

print(f"Class weights -> Not Risky: {class_weights[0]:.2f}, Risky: {class_weights[1]:.2f}")

def train_one_epoch():
    model.train()
    optimizer.zero_grad()
    out = model(data.x_dict, data.edge_index_dict)
    loss = F.cross_entropy(out[train_mask], labels[train_mask], weight=class_weights)
    loss.backward()
    optimizer.step()
    return loss.item()

def evaluate():
    model.eval()
    with torch.no_grad():
        out = model(data.x_dict, data.edge_index_dict)
        preds = out.argmax(dim=1)

        train_acc = (preds[train_mask] == labels[train_mask]).float().mean().item()
        test_acc = (preds[test_mask] == labels[test_mask]).float().mean().item()

    return train_acc, test_acc

# ============================================================
# TRAINING LOOP
# ============================================================

print()
print("Training...")
for epoch in range(1, 101):
    loss = train_one_epoch()
    if epoch % 10 == 0:
        train_acc, test_acc = evaluate()
        print(f"Epoch {epoch:3d} | Loss: {loss:.4f} | Train Acc: {train_acc:.3f} | Test Acc: {test_acc:.3f}")

print()
print("Training complete!")

from sklearn.metrics import classification_report, confusion_matrix

# ============================================================
# DETAILED EVALUATION (accuracy alone is misleading here)
# ============================================================

model.eval()
with torch.no_grad():
    out = model(data.x_dict, data.edge_index_dict)
    preds = out.argmax(dim=1)

test_preds = preds[test_mask].numpy()
test_labels = labels[test_mask].numpy()

print()
print("=" * 60)
print("DETAILED TEST SET RESULTS")
print("=" * 60)
print(classification_report(test_labels, test_preds, target_names=["Not Risky", "Risky"]))

print("Confusion Matrix:")
cm = confusion_matrix(test_labels, test_preds)
print(f"                Predicted Not-Risky   Predicted Risky")
print(f"Actual Not-Risky        {cm[0][0]:>4}                {cm[0][1]:>4}")
print(f"Actual Risky            {cm[1][0]:>4}                {cm[1][1]:>4}")

# ============================================================
# GENERALIZATION TEST — HIDDEN CONTRACT-RATE RULE
# Check both hard predictions AND raw risk scores
# ============================================================
hidden_mask = data["invoice"].hidden_test_mask

model.eval()
with torch.no_grad():
    out = model(data.x_dict, data.edge_index_dict)
    probs = F.softmax(out, dim=1)[:, 1]   # probability of "risky" per invoice
    preds = out.argmax(dim=1)

hidden_preds = preds[hidden_mask]
hidden_probs = probs[hidden_mask]
num_hidden = hidden_mask.sum().item()
num_caught = (hidden_preds == 1).sum().item()

# Compare: average risk score for hidden cases vs. average for normal invoices
normal_mask = (data["invoice"].y == 0) & (~hidden_mask)
avg_hidden_prob = hidden_probs.mean().item()
avg_normal_prob = probs[normal_mask].mean().item()

print()
print("=" * 60)
print("GENERALIZATION TEST — HIDDEN CONTRACT-RATE RULE")
print("=" * 60)
print(f"Hidden fraud cases (never trained on): {num_hidden}")
print(f"Caught by GNN (hard prediction): {num_caught}")
print(f"Generalization rate: {num_caught / num_hidden:.1%}")
print()
print(f"Avg risk score on hidden cases:  {avg_hidden_prob:.3f}")
print(f"Avg risk score on normal invoices: {avg_normal_prob:.3f}")
print()
print("Individual hidden-case risk scores:")
print(sorted(hidden_probs.tolist(), reverse=True))

# ============================================================
# Save per-invoice GNN scores for dashboard use
# ============================================================
# invoice_id order must match the graph's invoice node order —
# this assumes invoices were loaded into the graph in the same
# row order as invoices.csv (true if you built the graph via a
# straight pandas read with no reordering/filtering)
invoices_df = pd.read_csv("../../data/invoices.csv")

assert len(invoices_df) == probs.shape[0], (
    f"Mismatch: {len(invoices_df)} invoices in CSV vs {probs.shape[0]} nodes in graph — "
    "invoice_id order may not line up, do not trust this output until fixed"
)

gnn_results = pd.DataFrame({
    "invoice_id": invoices_df["invoice_id"],
    "gnn_risk_score": probs.tolist(),
    "gnn_prediction": preds.tolist(),  # 1 = risky, 0 = not risky
})
gnn_results.to_csv("../../data/gnn_scores.csv", index=False)
print(f"\nSaved {len(gnn_results)} GNN scores to ../../data/gnn_scores.csv")