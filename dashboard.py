import pandas as pd
import streamlit as st

st.set_page_config(page_title="SentinelP2P — Fraud Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("dashboard_data.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

st.title("SentinelP2P — Procurement Fraud Dashboard")

# --- Summary metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Invoices", len(df))
col2.metric("Flagged", int((df["overall_status"] == "Flagged").sum()))
col3.metric("Rule-Based Flags", int(df["any_rule_flagged"].sum()))
col4.metric("RAG Scope Mismatches", int((df["rag_status"] == "mismatch").sum()))

st.divider()

# --- Filters ---
st.sidebar.header("Filters")
status_filter = st.sidebar.multiselect(
    "Overall Status", options=df["overall_status"].unique(), default=["Flagged"]
)
# detection_filter = st.sidebar.multiselect(
#     "Detected By",
#     options=["Rule-based", "GNN", "RAG (scope mismatch)"],
#     default=[],
# )

filtered = df[df["overall_status"].isin(status_filter)] if status_filter else df

# if "Rule-based" in detection_filter:
#     filtered = filtered[filtered["any_rule_flagged"]]
# if "GNN" in detection_filter:
#     filtered = filtered[filtered["gnn_prediction"] == 1]
# if "RAG (scope mismatch)" in detection_filter:
#     filtered = filtered[filtered["rag_status"] == "mismatch"]

# st.subheader(f"Invoices ({len(filtered)})")
detection_filter = st.sidebar.multiselect(
    "Detected By",
    options=["GNN", "RAG (scope mismatch)"] + [c.replace("rule_", "") for c in df.columns if c.startswith("rule_")],
    default=[],
)

for method in detection_filter:
    if method == "GNN":
        filtered = filtered[filtered["gnn_prediction"] == 1]
    elif method == "RAG (scope mismatch)":
        filtered = filtered[filtered["rag_status"] == "mismatch"]
    else:
        filtered = filtered[filtered[f"rule_{method}"]]
display_cols = [
    "invoice_id", "amount", "item_category", "description", "date",
    "overall_status", "num_rules_flagged", "gnn_risk_score", "rag_status",
]
st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

# --- Invoice detail view ---
st.divider()
st.subheader("Invoice Detail")
selected_id = st.selectbox("Select an invoice to inspect", options=filtered["invoice_id"])

if selected_id:
    row = df[df["invoice_id"] == selected_id].iloc[0]
    c1, c2 = st.columns(2)

    with c1:
        st.write("**Invoice Info**")
        st.write(f"Amount: ₹{row['amount']:,.2f}")
        st.write(f"Category: {row['item_category']}")
        st.write(f"Description: {row['description']}")
        st.write(f"Date: {row['date'].date()}")
        st.write(f"Payment status: {row['payment_status']}")

    with c2:
        st.write("**Risk Signals**")
        st.write(f"GNN risk score: {row['gnn_risk_score']:.3f}")
        st.write(f"RAG status: {row['rag_status']}")
        if pd.notna(row.get("similarity")):
            st.write(f"RAG similarity: {row['similarity']:.3f}")

        rule_cols = [c for c in df.columns if c.startswith("rule_")]
        fired_rules = [c.replace("rule_", "") for c in rule_cols if row[c]]
        st.write(f"Rules fired: {', '.join(fired_rules) if fired_rules else 'None'}")