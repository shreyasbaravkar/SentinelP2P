import os
import shutil
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

THRESHOLD = 0.50

if not os.path.exists("rag_similarity_scores_v1.csv"):
    shutil.copy("rag_similarity_scores.csv", "rag_similarity_scores_v1.csv")

r = pd.read_csv("rag_similarity_scores_v1.csv")
inv = pd.read_csv("invoices.csv")[["invoice_id", "description"]]
df = r.merge(inv, on="invoice_id", how="left")

df["desc_clean"] = df["description"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
df["service"] = df["contract_text"].str.extract(r"(?:provide|supply) (.*?) at an agreed")[0]

can_score = df["service"].notna() & df["desc_clean"].notna()
model = SentenceTransformer("all-MiniLM-L6-v2")
uniq = sorted(set(df.loc[can_score, "desc_clean"]) | set(df.loc[can_score, "service"]))
vecs = dict(zip(uniq, model.encode(uniq, normalize_embeddings=True)))

df["similarity_full"] = df["similarity"]  # old whole-sentence score, kept for reference
df["similarity"] = [
    float(np.dot(vecs[d], vecs[s])) if ok else np.nan
    for d, s, ok in zip(df["desc_clean"], df["service"], can_score)
]

def status(row):
    if pd.isna(row["contract_text"]):
        return "no_contract_on_file"
    if row["desc_clean"] == "Contract rate mismatch case" or pd.isna(row["similarity"]):
        return "not_assessable"  # description is a fraud label, not a real service
    return "mismatch" if row["similarity"] < THRESHOLD else "ok"

df["rag_status"] = df.apply(status, axis=1)
df.loc[df["rag_status"] == "not_assessable", "similarity"] = np.nan

df[["invoice_id", "vendor_id", "contract_text", "similarity", "similarity_full", "rag_status"]] \
    .to_csv("rag_similarity_scores.csv", index=False)
print(df["rag_status"].value_counts())