import pandas as pd

invoices = pd.read_csv("invoices.csv")
rules = pd.read_csv("rule_flags.csv")
gnn = pd.read_csv("gnn_scores.csv")
rag = pd.read_csv("rag_similarity_scores.csv")

print("Rows -> invoices:", len(invoices), "| rules:", len(rules), "| gnn:", len(gnn), "| rag:", len(rag))

combined = invoices[["invoice_id", "po_id", "amount", "item_category", "description",
                     "date", "payment_status", "submitted_by_employee_id"]].copy()
combined = combined.merge(rules, on="invoice_id", how="left")
combined = combined.merge(gnn, on="invoice_id", how="left")
combined = combined.merge(rag[["invoice_id", "similarity", "rag_status","best_match_service"]], on="invoice_id", how="left")

rule_cols = [c for c in combined.columns if c.startswith("rule_")]
combined["any_rule_flagged"] = combined[rule_cols].any(axis=1)
combined["num_rules_flagged"] = combined[rule_cols].sum(axis=1)

def overall_status(row):
    if row["any_rule_flagged"] or row["gnn_prediction"] == 1:
        return "Flagged"
    return "Clear"

combined["overall_status"] = combined.apply(overall_status, axis=1)
combined.to_csv("dashboard_data.csv", index=False)

print(combined["overall_status"].value_counts())
print(combined["rag_status"].value_counts(dropna=False))