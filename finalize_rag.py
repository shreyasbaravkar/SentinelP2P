import os
import shutil
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

MARGIN = 0.10  # vendor's service must score within this much of the best-matching service

if not os.path.exists("rag_similarity_scores_v1.csv"):
    shutil.copy("rag_similarity_scores.csv", "rag_similarity_scores_v1.csv")

SERVICE_RE = r"(?:provide|supply) (.*?) at an agreed"

r = pd.read_csv("rag_similarity_scores_v1.csv")
inv = pd.read_csv("invoices.csv")[["invoice_id", "description"]]
contracts = pd.read_csv("contracts.csv")

services = sorted(contracts["contract_text"].str.extract(SERVICE_RE)[0].dropna().unique())
print("Services found in contracts:", services)

df = r.merge(inv, on="invoice_id", how="left")
df["desc_clean"] = df["description"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
df["vendor_service"] = df["contract_text"].str.extract(SERVICE_RE)[0]

assessable = (
    df["vendor_service"].notna()
    & df["desc_clean"].notna()
    & (df["desc_clean"] != "Contract rate mismatch case")
)

model = SentenceTransformer("all-MiniLM-L6-v2")
descs = sorted(df.loc[assessable, "desc_clean"].unique())
dvec = dict(zip(descs, model.encode(descs, normalize_embeddings=True)))
svec = model.encode(services, normalize_embeddings=True)
sidx = {s: i for i, s in enumerate(services)}

own, best, best_service = [], [], []
for d, vs, ok in zip(df["desc_clean"], df["vendor_service"], assessable):
    if not ok:
        own.append(np.nan)
        best.append(np.nan)
        best_service.append(None)
        continue
    sims = svec @ dvec[d]
    own.append(float(sims[sidx[vs]]))
    best.append(float(sims.max()))
    best_service.append(services[int(sims.argmax())])

df["similarity_full"] = df["similarity"]  # old whole-sentence score, kept for reference
df["similarity"] = own
df["best_match_score"] = best
df["best_match_service"] = best_service


def status(row):
    if pd.isna(row["contract_text"]):
        return "no_contract_on_file"
    if pd.isna(row["similarity"]):
        return "not_assessable"  # description is a fraud label, not a real service
    return "ok" if row["similarity"] >= row["best_match_score"] - MARGIN else "mismatch"


df["rag_status"] = df.apply(status, axis=1)

cols = ["invoice_id", "vendor_id", "contract_text", "similarity", "best_match_service",
        "best_match_score", "similarity_full", "rag_status"]
df[cols].to_csv("rag_similarity_scores.csv", index=False)

print()
print(df["rag_status"].value_counts())

a = df[df["similarity"].notna()]
print(f"\nMismatches among {len(a)} assessable invoices, by margin:")
for m in [0.05, 0.10, 0.15, 0.20]:
    print(f"  margin {m:.2f}: {(a['similarity'] < a['best_match_score'] - m).sum()}")
print(f"  old fixed 0.50 cutoff: {(a['similarity'] < 0.50).sum()}")