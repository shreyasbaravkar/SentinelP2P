import pandas as pd
import streamlit as st
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

st.set_page_config(page_title="SentinelP2P — Fraud Dashboard", layout="wide")

# --- Custom CSS Styling Injection ---
st.markdown("""
    <style>
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .card-container {
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        height: 100%;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv("dashboard_data.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

st.title("SentinelP2P — Procurement Fraud Dashboard")

# --- Summary metrics (Card Styled) ---
col1, col2, col3, col4 = st.columns(4)

total_invoices = len(df)
flagged_count = int((df["overall_status"] == "Flagged").sum())
rule_flags = int(df["any_rule_flagged"].sum())
rag_mismatches = int((df["rag_status"] == "mismatch").sum())

with col1:
    st.markdown(f"""
        <div class="metric-card">
            <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">Total Invoices</p>
            <h3 style="color: #0f172a; font-size: 26px; font-weight: 800; margin: 0;">{total_invoices}</h3>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-card">
            <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">Flagged</p>
            <h3 style="color: #dc2626; font-size: 26px; font-weight: 800; margin: 0;">{flagged_count}</h3>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="metric-card">
            <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">Rule-Based Flags</p>
            <h3 style="color: #2563eb; font-size: 26px; font-weight: 800; margin: 0;">{rule_flags}</h3>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="metric-card">
            <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">RAG Scope Mismatches</p>
            <h3 style="color: #4f46e5; font-size: 26px; font-weight: 800; margin: 0;">{rag_mismatches}</h3>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# --- Filters ---
st.sidebar.header("Filters")
status_filter = st.sidebar.multiselect(
    "Overall Status", options=df["overall_status"].unique(), default=["Flagged"]
)

filtered = df[df["overall_status"].isin(status_filter)] if status_filter else df

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

st.subheader(f"Transaction Risk Matrix ({len(filtered)} results)")
display_cols = [
    "invoice_id", "amount", "item_category", "description", "date",
    "overall_status", "num_rules_flagged", "gnn_risk_score", "rag_status",
]
filtered_display = filtered.copy()
filtered_display["gnn_risk_score"] = filtered_display["gnn_risk_score"].apply(lambda x: f"{x:.1%}")
st.dataframe(filtered_display[display_cols], use_container_width=True, hide_index=True)

# --- Invoice detail view ---
st.divider()
st.subheader("🔍 Forensic Invoice Inspector")

if len(filtered) > 0:
    selected_id = st.selectbox("Select an invoice to inspect", options=filtered["invoice_id"])
else:
    selected_id = st.selectbox("Select an invoice to inspect", options=df["invoice_id"])

if selected_id:
    row = df[df["invoice_id"] == selected_id].iloc[0]
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"""
            <div class="card-container">
                <h4 style="color: #0f172a; font-size: 15px; font-weight: 700; margin-top: 0; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">Invoice Core Attributes</h4>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>Selected ID:</b> <span style="font-family: monospace; color: #2563eb;">{selected_id}</span></p>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>Amount:</b> ₹{row['amount']:,.2f}</p>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>Category:</b> {row['item_category']}</p>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>Description:</b> {row['description']}</p>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>Date:</b> {row['date'].date()}</p>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>Payment status:</b> {row['payment_status']}</p>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        rule_cols = [c for c in df.columns if c.startswith("rule_")]
        fired_rules = [c.replace("rule_", "") for c in rule_cols if row[c]]
        fired_rules_str = ', '.join(fired_rules) if fired_rules else 'None'
        
        similarity_str = f"{row['similarity']:.1%}" if pd.notna(row.get("similarity")) else "N/A"
        gnn_pct = f"{row['gnn_risk_score']:.1%}"

        st.markdown(f"""
            <div class="card-container">
                <h4 style="color: #0f172a; font-size: 15px; font-weight: 700; margin-top: 0; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">Multi-Modal Risk Telemetry</h4>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>GNN Risk Score:</b> <span style="color: #dc2626; font-weight: 700;">{gnn_pct}</span></p>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>RAG Status:</b> <span style="color: #d97706; font-weight: 600;">{row['rag_status']}</span></p>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>RAG Similarity:</b> {similarity_str}</p>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;"><b>Rules Fired:</b> <span style="font-family: monospace; background: #fef2f2; color: #dc2626; padding: 2px 6px; border-radius: 4px;">{fired_rules_str}</span></p>
            </div>
        """, unsafe_allow_html=True)


st.divider()
st.subheader("🔍 Contract Search (Investigator Tool)")
st.caption("Ask a question about the contracts on file — e.g. 'which contract covers catering services?'")

@st.cache_resource
def load_search_index():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = QdrantClient(path="./qdrant_data")
    return model, client

search_model, search_client = load_search_index()

query = st.text_input("Search contracts")

if query:
    query_vec = search_model.encode(query).tolist()
    hits = search_client.query_points(
        collection_name="contracts",
        query=query_vec,
        limit=15,
    ).points

    for hit in hits:
        payload = hit.payload
        st.markdown(f"""
            <div style="background-color: white; padding: 16px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px;">
                <b>{payload['contract_id']}</b> — Vendor: {payload['vendor_id']} (score: {hit.score:.1%})<br>
                <p style="color: #475569; font-size: 13px; margin-top: 6px;">{payload["contract_text"]}</p>
            </div>
        """, unsafe_allow_html=True)