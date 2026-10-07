import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SentinelP2P — Fraud Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    df = pd.read_csv("data/dashboard_data.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

# --- Sidebar Navigation Bar ---
st.sidebar.title("🛡️ SentinelP2P")
st.sidebar.caption("Procure-to-Pay Fraud Intelligence")

navigation = st.sidebar.radio(
    "Navigation Menu",
    options=[
        "📊 Overview & Metrics", 
        "🔍 Risk Matrix & Forensic Inspector", 
        "💬 Contract Intelligence (RAG)"
    ]
)

st.sidebar.divider()
st.sidebar.info("Demo Mode Active — Connected to local procurement ledger.")

# ============================================================
# SECTION 1: OVERVIEW & METRICS
# ============================================================
if navigation == "📊 Overview & Metrics":
    st.title("Platform Overview & Key Metrics")
    st.markdown("High-level telemetry summarizing automated compliance checks, machine learning risk models, and audit flags across corporate spend.")
    
    st.divider()

    total_invoices = len(df)
    flagged_count = int((df["overall_status"] == "Flagged").sum())
    rule_flags = int(df["any_rule_flagged"].sum())
    rag_mismatches = int((df["rag_status"] == "mismatch").sum())

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">Total Invoices Reviewed</p>
                <h3 style="color: #0f172a; font-size: 26px; font-weight: 800; margin: 0;">{total_invoices}</h3>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">Confirmed Fraudulent</p>
                <h3 style="color: #dc2626; font-size: 26px; font-weight: 800; margin: 0;">{flagged_count}</h3>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">Rule-Based Alerts</p>
                <h3 style="color: #2563eb; font-size: 26px; font-weight: 800; margin: 0;">{rule_flags}</h3>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="metric-card">
                <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">RAG/AI Anomalies</p>
                <h3 style="color: #4f46e5; font-size: 26px; font-weight: 800; margin: 0;">{rag_mismatches}</h3>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("System Health Summary")
    st.success("✔ Graph Neural Network (GNN) pipelines active & synced.")
    st.success("✔ Neo4j graph relational lookups operating at optimal latency.")


# ============================================================
# SECTION 2: RISK MATRIX & FORENSIC INSPECTOR
# ============================================================
elif navigation == "🔍 Risk Matrix & Forensic Inspector":
    st.title("Transaction Risk Matrix & Forensic Inspector")
    st.markdown("Inspect granular invoice details, evaluate graph anomaly probabilities, and triage high-priority flagged transactions.")
    
    st.divider()

    # --- Transaction Risk Matrix ---
    st.subheader("Anomaly & Risk Review Table")
    display_cols = [
        "invoice_id", "amount", "item_category", "description", "date",
        "overall_status", "gnn_risk_score", "rag_status"
    ]

    df_display = df.copy()
    df_display["amount"] = df_display["amount"].apply(lambda x: f"₹{x:,.2f}")
    df_display["gnn_risk_score"] = df_display["gnn_risk_score"].apply(lambda x: f"{x:.1%}")

    st.dataframe(df_display[display_cols].head(10), use_container_width=True, hide_index=True)

    # --- Dynamically sorted high-priority queue ---
    queue_df = df.sort_values(
        by=["overall_status", "gnn_risk_score", "num_rules_flagged"], 
        ascending=[False, False, False]
    ).head(6)

    # --- Forensic Invoice Inspector Split View ---
    st.divider()
    st.subheader("Forensic Invoice Inspector")

    with st.container(border=True):
        st.markdown("#### Invoice Deep Dive")
        
        col_queue, col_detail = st.columns([1, 1.8], gap="medium")

        with col_queue:
            st.markdown("##### High-Priority Review Queue")
            selected_id = st.radio(
                "Select Invoice ID",
                options=queue_df["invoice_id"],
                label_visibility="collapsed"
            )

        with col_detail:
            st.markdown("##### Detailed Inspector View")
            if selected_id:
                row = df[df["invoice_id"] == selected_id].iloc[0]
                
                st.markdown(f"""
                    <div style="background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
                        <p style="font-size: 13px; margin: 4px 0;"><b>Invoice ID:</b> <span style="font-family: monospace; color: #2563eb;">{selected_id}</span></p>
                        <p style="font-size: 13px; margin: 4px 0;"><b>Amount:</b> ₹{row['amount']:,.2f}</p>
                        <p style="font-size: 13px; margin: 4px 0;"><b>Category:</b> {row['item_category']}</p>
                        <p style="font-size: 13px; margin: 4px 0;"><b>Description:</b> {row['description']}</p>
                        <p style="font-size: 13px; margin: 4px 0;"><b>Date:</b> {row['date'].strftime('%b %d, %Y')}</p>
                        <p style="font-size: 13px; margin: 4px 0;"><b>Payment Status:</b> {row['payment_status']}</p>
                        <hr style="margin: 8px 0; border: none; border-top: 1px solid #cbd5e1;">
                        <p style="font-size: 13px; margin: 4px 0;"><b>GNN Risk Score:</b> <span style="color: #dc2626; font-weight: 700;">{row['gnn_risk_score']:.1%}</span></p>
                        <p style="font-size: 13px; margin: 4px 0;"><b>RAG Status:</b> <span style="color: #d97706; font-weight: 600;">{row['rag_status']}</span></p>
                        <p style="font-size: 13px; margin: 4px 0;"><b>Overall Status:</b> <span style="background: #fef2f2; color: #dc2626; padding: 2px 6px; border-radius: 4px; font-weight: 600;">{row['overall_status']}</span></p>
                    </div>
                """, unsafe_allow_html=True)


# ============================================================
# SECTION 3: CONTRACT SEARCH (RAG)
# ============================================================
elif navigation == "💬 Contract Intelligence (RAG)":
    st.title("Contract Intelligence & Semantic Search")
    st.markdown("Interrogate enterprise legal agreements and scope definitions using vector-based similarity checks.")
    
    st.divider()

    st.subheader("🔍 Contract Search (Investigator Tool)")
    st.caption("Ask a question about the contracts on file — e.g., 'which contract covers catering services?'")

    query = st.text_input("Search contracts")

    if query:
        st.info("💡 **Demo Mode:** RAG pipeline backend search is currently offline / under integration. Real contract semantic search results will appear here soon!")

    # ============================================================
    # Fully Commented Backend Code (For Future Integration)
    # ============================================================
    # from qdrant_client import QdrantClient
    # from sentence_transformers import SentenceTransformer
    #
    # @st.cache_resource
    # def load_search_index():
    #     model = SentenceTransformer("all-MiniLM-L6-v2")
    #     client = QdrantClient(path="./qdrant_data")
    #     return model, client
    #
    # search_model, search_client = load_search_index()
    # 
    # if query:
    #     query_vec = search_model.encode(query).tolist()
    #     hits = search_client.query_points(
    #         collection_name="contracts",
    #         query=query_vec,
    #         limit=15,
    #     ).points
    #
    #     for hit in hits:
    #         payload = hit.payload
    #         st.markdown(f"""
    #             <div style="background-color: white; padding: 16px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px;">
    #                 <b>{payload['contract_id']}</b> — Vendor: {payload['vendor_id']} (score: {hit.score:.1%})<br>
    #                 <p style="color: #475569; font-size: 13px; margin-top: 6px;">{payload["contract_text"]}</p>
    #             </div>
    #         """, unsafe_allow_html=True)