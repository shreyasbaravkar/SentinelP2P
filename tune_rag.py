import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

r = pd.read_csv("rag_similarity_scores.csv")
inv = pd.read_csv("invoices.csv")[["invoice_id", "description"]]
df = r.dropna(subset=["similarity"]).merge(inv, on="invoice_id")

df["desc_clean"] = df["description"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
df["service"] = df["contract_text"].str.extract(r"(?:provide|supply) (.*?) at an agreed")[0]

# Which contract service each description SHOULD belong to (used only as ground truth)
expected = {
    "Printing and packaging materials": "printing and packaging materials",
    "Software license renewal": "software licenses",
    "Logistics and courier services": "logistics and courier services",
    "Office stationery supply": "office supplies",
    "Catering services": "catering services",
    "IT hardware procurement": "IT hardware equipment",
    "Cleaning services": "cleaning services",
    "Furniture purchase": "office supplies",
    # "Contract rate mismatch case" left out on purpose (it's a fraud label, not a real service)
}
df["expected_service"] = df["desc_clean"].map(expected)
ev = df[df["expected_service"].notna()].copy()
ev["true_mismatch"] = ev["expected_service"] != ev["service"]

# Re-score: description vs service phrase only
model = SentenceTransformer("all-MiniLM-L6-v2")
uniq = list(set(ev["desc_clean"]) | set(ev["service"]))
vecs = dict(zip(uniq, model.encode(uniq, normalize_embeddings=True)))
ev["service_sim"] = [float(np.dot(vecs[d], vecs[s])) for d, s in zip(ev["desc_clean"], ev["service"])]

print(f"Evaluable invoices: {len(ev)} | true mismatches: {ev['true_mismatch'].sum()} | true matches: {(~ev['true_mismatch']).sum()}")
print(f"Left out (Furniture / Contract rate mismatch case): {len(df) - len(ev)}\n")

def report(col, thresholds):
    print(f"--- {col} ---")
    print("score range, true matches:   ", ev.loc[~ev.true_mismatch, col].min().round(3), "to", ev.loc[~ev.true_mismatch, col].max().round(3))
    print("score range, true mismatches:", ev.loc[ev.true_mismatch, col].min().round(3), "to", ev.loc[ev.true_mismatch, col].max().round(3))
    for t in thresholds:
        flagged = ev[col] < t
        tp = (flagged & ev.true_mismatch).sum()
        prec = tp / flagged.sum() if flagged.sum() else float("nan")
        rec = tp / ev.true_mismatch.sum()
        print(f"threshold {t:.2f}: flagged {flagged.sum():3d} | precision {prec:.2f} | recall {rec:.2f}")
    print()

report("similarity", [0.10, 0.20, 0.30, 0.40])
report("service_sim", [0.30, 0.40, 0.50, 0.60, 0.70])

ev.to_csv("rag_eval.csv", index=False)