import streamlit as st
import pandas as pd
from engine import evaluate_buy_gates, calculate_confidence  # Your functions

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two-Stage Discovery + Authoritative Logic Engine")

if "dsr_discovery_df" not in st.session_state:
    st.session_state.dsr_discovery_df = None
if "explorer_df" not in st.session_state:
    st.session_state.explorer_df = None

client_mode = st.radio("Client Type", ("DSR Upload", "Explorer"))

st.markdown("## 🟩 Stage 1 — Discovery Filters")

state = st.selectbox("State", ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"])
max_dom = st.slider("Max Days on Market", 0, 180, 90)
max_price = st.slider("Max Median Price ($)", 200_000, 2_000_000, 1_000_000, step=50_000)
min_yield = st.slider("Min Yield (%)", 3.0, 8.0, 4.0)

def filter_df(df, state, max_dom, max_price, min_yield):
    if df is None or df.empty:
        return pd.DataFrame()
    filtered = df[
        (df["Days on Market"] <= max_dom) &
        (df["Median 12 months"] <= max_price) &
        (pd.to_numeric(df.get("Yield %", 0), errors='coerce') >= min_yield)
    ].copy()
    if state != "All":
        filtered = filtered[filtered["State"] == state]
    return filtered

if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload DSR Excel", type="xlsx")
    if uploaded_file:
        st.session_state.dsr_discovery_df = pd.read_excel(uploaded_file)
        current_df = filter_df(st.session_state.dsr_discovery_df, state, max_dom, max_price, min_yield)
    else:
        current_df = pd.DataFrame()
else:
    if st.session_state.explorer_df is None:
        try:
            st.session_state.explorer_df = pd.read_csv("explorer_data.csv")
        except FileNotFoundError:
            st.error("Add explorer_data.csv or use DSR.")
            st.stop()
    current_df = filter_df(st.session_state.explorer_df, state, max_dom, max_price, min_yield)

if not current_df.empty:
    st.markdown(f"## 📍 Discovery ({len(current_df)} suburbs)")
    display_cols = ["Suburb"]
    if "Yield %" in current_df:
        display_cols.append("Yield %")
    df_display = current_df[["State"] + display_cols].copy()
    if "Median 12 months" in current_df:
        df_display["Median Price"] = current_df["Median 12 months"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
    st.dataframe(df_display, use_container_width=True)
    selected_suburbs = st.multiselect("Stage 2 suburbs", current_df["Suburb"].tolist())
else:
    st.info("No matches.")
    selected_suburbs = []

if selected_suburbs:
    st.markdown("## 🟥 Stage 2 — Your Engine")
    for suburb in selected_suburbs:
        row = current_df[current_df["Suburb"] == suburb].iloc[0]
        # Build factors dict from row (your data keys → engine keys)
        factors = {
            "renters_pct": row.get("Renters %", 20),
            "vacancy_pct": row.get("Vacancy rate", 1.5),
            "demand_supply_ratio": row.get("Demand Supply Ratio", 60),
            "stock_on_market_pct": row.get("Stock on Market %", 1.0),
            "gross_rental_yield": row.get("Yield %", 4.5),
            "statistical_reliability": row.get("Reliability", 70)
        }
        decision, failed_gates = evaluate_buy_gates(factors)
        conf_score, conf_band = calculate_confidence(decision)
        
        with st.expander(suburb):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Decision", decision)
                st.metric("Conf Score", conf_score)
                st.metric("Conf Band", conf_band)
            with col2:
                st.write("**Failed Gates:**", failed_gates)
                st.write("**Narrative:**", "All gates passed." if decision == "BUY" else "Review failed gates.")
            
            if st.button("Save", key=suburb):
                st.session_state.setdefault("shortlist", []).append(suburb)
                st.rerun()

if st.session_state.get("shortlist"):
    st.markdown("## 📋 Shortlist")
    st.write(st.session_state.shortlist)
