import re
import pandas as pd
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

scores = pd.read_csv("rag_similarity_scores.csv")
inv = pd.read_csv("invoices.csv")[["invoice_id", "description"]]

df = scores[scores["rag_status"] == "mismatch"].merge(inv, on="invoice_id", how="left")
df["desc_clean"] = df["description"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()


def service_of(text):
    m = re.search(r"(?:provide|supply) (.*?) at an agreed", text or "")
    return m.group(1) if m else None


model = SentenceTransformer("all-MiniLM-L6-v2")
client = QdrantClient(path="./qdrant_data")

rows = []
for _, r in df.iterrows():
    vec = model.encode(r["desc_clean"]).tolist()
    hits = client.query_points(collection_name="contracts", query=vec, limit=5).points
    rows.append({
        "invoice_id": r["invoice_id"],
        "vendor_id": r["vendor_id"],
        "description": r["description"],
        "vendor_contract_service": service_of(r["contract_text"]),
        "closest_service_in_contracts": service_of(hits[0].payload["contract_text"]),
        "closest_contract_ids": ", ".join(h.payload["contract_id"] for h in hits[:3]),
        "closest_contract_score": round(hits[0].score, 3),
    })

out = pd.DataFrame(rows)
out.to_csv("rag_evidence.csv", index=False)
print(f"Saved evidence for {len(out)} mismatched invoices")
print(out.head(10).to_string())