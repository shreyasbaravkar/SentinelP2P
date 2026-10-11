import os

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SentinelP2P — Fraud Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
    <style>
    .metric-card, .card-container, .inspector-card, .search-card {
        background-color: white;
        color: #0f172a;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-card { padding: 20px; }
    .card-container { padding: 24px; height: 100%; }
    .inspector-card { background-color: #f8fafc; padding: 16px; border-radius: 8px; box-shadow: none; }
    .search-card { padding: 16px; border-radius: 10px; margin-bottom: 10px; }
    .inspector-card p, .search-card p { color: #475569; }
    </style>
""", unsafe_allow_html=True)

# Looks in the main folder first, then in data/
DATA_PATHS = ["dashboard_data.csv", "data/dashboard_data.csv"]


@st.cache_data
def load_data():
    path = next((p for p in DATA_PATHS if os.path.exists(p)), None)
    if path is None:
        return None, None
    data = pd.read_csv(path)
    data["date"] = pd.to_datetime(data["date"])
    data["gnn_risk_score"] = data["gnn_risk_score"].fillna(0.0)
    data["gnn_prediction"] = data["gnn_prediction"].fillna(0).astype(int)
    data["rag_status"] = data["rag_status"].fillna("n/a")
    data["is_flagged"] = (data["overall_status"] == "Flagged").astype(int)
    return data, path


df, data_path = load_data()
if df is None:
    st.error("dashboard_data.csv not found. Run `python build_dashboard_data.py` first.")
    st.stop()

RULE_COLS = [c for c in df.columns if c.startswith("rule_")]


def pretty(rule_col):
    return rule_col.replace("rule_", "").replace("_", " ")


# --- Sidebar navigation ---
st.sidebar.title("🛡️ SentinelP2P")
st.sidebar.caption("Procure-to-Pay Fraud Intelligence")

navigation = st.sidebar.radio(
    "Navigation Menu",
    options=[
        "📊 Overview & Metrics",
        "🔍 Risk Matrix & Forensic Inspector",
        "💬 Contract Intelligence (RAG)",
    ],
)

st.sidebar.divider()
st.sidebar.info(f"Data source: `{data_path}` ({len(df)} invoices)")


def metric_card(label, value, color):
    return f"""
        <div class="metric-card">
            <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">{label}</p>
            <h3 style="color: {color}; font-size: 26px; font-weight: 800; margin: 0;">{value}</h3>
        </div>
    """


# ============================================================
# SECTION 1: OVERVIEW & METRICS
# ============================================================
if navigation == "📊 Overview & Metrics":
    st.title("Platform Overview & Key Metrics")
    st.markdown("Summary of rule-based checks, the GNN risk model and contract scope matching across all invoices.")
    st.divider()

    total_invoices = len(df)
    flagged_count = int(df["is_flagged"].sum())
    rule_flags = int(df["any_rule_flagged"].sum())
    rag_mismatches = int((df["rag_status"] == "mismatch").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Total Invoices", total_invoices, "#0f172a"), unsafe_allow_html=True)
    c2.markdown(metric_card("Flagged for Review", flagged_count, "#dc2626"), unsafe_allow_html=True)
    c3.markdown(metric_card("Rule-Based Alerts", rule_flags, "#2563eb"), unsafe_allow_html=True)
    c4.markdown(metric_card("RAG Scope Mismatches", rag_mismatches, "#4f46e5"), unsafe_allow_html=True)

    st.caption(
        "Flagged for Review = any rule fired or the GNN predicted risky. RAG scope mismatches are counted "
        "separately: in this synthetic dataset most invoice descriptions are unrelated to the vendor's contract."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns(2)

    with left:
        st.subheader("Who caught what")
        by_rules = df["any_rule_flagged"].astype(bool)
        by_gnn = df["gnn_prediction"] == 1
        overlap = pd.DataFrame({
            "Caught by": ["Rules only", "GNN only", "Both rules and GNN", "Neither"],
            "Invoices": [
                int((by_rules & ~by_gnn).sum()),
                int((~by_rules & by_gnn).sum()),
                int((by_rules & by_gnn).sum()),
                int((~by_rules & ~by_gnn).sum()),
            ],
        })
        st.dataframe(overlap, hide_index=True, use_container_width=True)

    with right:
        st.subheader("Contract scope check (RAG)")
        rag_counts = df["rag_status"].value_counts().rename_axis("RAG status").reset_index(name="Invoices")
        st.dataframe(rag_counts, hide_index=True, use_container_width=True)

    st.subheader("Rule alerts by type")
    rule_counts = pd.DataFrame({
        "Rule": [pretty(c) for c in RULE_COLS],
        "Invoices": [int(df[c].sum()) for c in RULE_COLS],
    })
    st.dataframe(rule_counts, hide_index=True, use_container_width=True)


# ============================================================
# SECTION 2: RISK MATRIX & FORENSIC INSPECTOR
# ============================================================
elif navigation == "🔍 Risk Matrix & Forensic Inspector":
    st.title("Transaction Risk Matrix & Forensic Inspector")
    st.markdown("Filter invoices by status or detection method, then inspect any invoice in detail.")
    st.divider()

    f1, f2 = st.columns(2)
    status_filter = f1.multiselect(
        "Overall Status", options=sorted(df["overall_status"].unique()), default=["Flagged"]
    )
    detection_filter = f2.multiselect(
        "Detected By (must match all selected)",
        options=["GNN", "RAG (scope mismatch)"] + [pretty(c) for c in RULE_COLS],
        default=[],
    )

    filtered = df[df["overall_status"].isin(status_filter)] if status_filter else df
    for method in detection_filter:
        if method == "GNN":
            filtered = filtered[filtered["gnn_prediction"] == 1]
        elif method == "RAG (scope mismatch)":
            filtered = filtered[filtered["rag_status"] == "mismatch"]
        else:
            filtered = filtered[filtered["rule_" + method.replace(" ", "_")].astype(bool)]

    filtered = filtered.sort_values(
        by=["is_flagged", "num_rules_flagged", "gnn_risk_score"], ascending=False
    )

    st.subheader(f"Anomaly & Risk Review Table ({len(filtered)} results)")
    display = filtered[[
        "invoice_id", "amount", "item_category", "description", "date",
        "overall_status", "num_rules_flagged", "gnn_risk_score", "rag_status",
    ]].copy()
    display["gnn_risk_score"] = display["gnn_risk_score"] * 100

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
            "date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            "gnn_risk_score": st.column_config.NumberColumn("GNN risk", format="%.1f%%"),
            "num_rules_flagged": st.column_config.NumberColumn("Rules fired"),
            "rag_status": st.column_config.TextColumn("RAG status"),
        },
    )

    st.divider()
    st.subheader("Forensic Invoice Inspector")

    if filtered.empty:
        st.info("No invoices match the current filters.")
        st.stop()

    with st.container(border=True):
        st.markdown("#### Invoice Deep Dive")
        col_queue, col_detail = st.columns([1, 1.8], gap="medium")

        with col_queue:
            st.markdown("##### High-Priority Review Queue")
            queue_ids = filtered["invoice_id"].head(8).tolist()
            queue_pick = st.radio("Select Invoice ID", options=queue_ids, label_visibility="collapsed")
            lookup = st.selectbox(
                "Or pick any invoice from the results",
                options=["— use the queue —"] + filtered["invoice_id"].tolist(),
            )
            selected_id = queue_pick if lookup == "— use the queue —" else lookup

        with col_detail:
            st.markdown("##### Detailed Inspector View")
            row = df[df["invoice_id"] == selected_id].iloc[0]

            fired = [pretty(c) for c in RULE_COLS if bool(row[c])]
            fired_str = ", ".join(fired) if fired else "None"
            similarity_str = f"{row['similarity']:.1%}" if pd.notna(row.get("similarity")) else "N/A"

            st.markdown(f"""
                <div class="inspector-card">
                    <p style="font-size: 13px; margin: 4px 0;"><b>Invoice ID:</b> <span style="font-family: monospace; color: #2563eb;">{selected_id}</span></p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>Amount:</b> ₹{row['amount']:,.2f}</p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>Category:</b> {row['item_category']}</p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>Description:</b> {row['description']}</p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>Date:</b> {row['date'].strftime('%b %d, %Y')}</p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>Payment Status:</b> {row['payment_status']}</p>
                    <hr style="margin: 8px 0; border: none; border-top: 1px solid #cbd5e1;">
                    <p style="font-size: 13px; margin: 4px 0;"><b>GNN Risk Score:</b> <span style="color: #dc2626; font-weight: 700;">{row['gnn_risk_score']:.1%}</span></p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>RAG Status:</b> <span style="color: #d97706; font-weight: 600;">{row['rag_status']}</span></p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>RAG Similarity:</b> {similarity_str}</p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>Rules Fired:</b> <span style="font-family: monospace; background: #fef2f2; color: #dc2626; padding: 2px 6px; border-radius: 4px;">{fired_str}</span></p>
                    <p style="font-size: 13px; margin: 4px 0;"><b>Overall Status:</b> <span style="background: #fef2f2; color: #dc2626; padding: 2px 6px; border-radius: 4px; font-weight: 600;">{row['overall_status']}</span></p>
                </div>
            """, unsafe_allow_html=True)


# ============================================================
# SECTION 3: CONTRACT SEARCH (RAG)
# ============================================================
elif navigation == "💬 Contract Intelligence (RAG)":
    st.title("Contract Intelligence & Semantic Search")
    st.markdown("Search the 157 contracts on file by meaning, not just keywords.")
    st.divider()

    st.subheader("🔍 Contract Search (Investigator Tool)")
    st.caption("Ask a question about the contracts on file — e.g. 'which contract covers catering services?'")

    @st.cache_resource
    def load_search_index():
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        client = QdrantClient(path="./qdrant_data")
        return model, client

    query = st.text_input("Search contracts")

    if query:
        try:
            search_model, search_client = load_search_index()
            query_vec = search_model.encode(query).tolist()
            hits = search_client.query_points(
                collection_name="contracts",
                query=query_vec,
                limit=10,
            ).points
        except Exception as e:
            st.error(
                "Contract search could not start. Make sure `python build_contract_index.py` "
                f"has been run and that no other program is using `qdrant_data`. Details: {e}"
            )
            st.stop()

        st.caption("Score = how close the contract's meaning is to your search (higher is closer).")
        for hit in hits:
            p = hit.payload
            st.markdown(f"""
                <div class="search-card">
                    <b>{p['contract_id']}</b> — Vendor: {p['vendor_id']} (score: {hit.score:.1%})<br>
                    <p style="font-size: 13px; margin-top: 6px;">{p['contract_text']}</p>
                </div>
            """, unsafe_allow_html=True)