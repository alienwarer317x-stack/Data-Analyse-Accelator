import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two-Stage Discovery + Authoritative Logic Engine")

# ====================== SESSION STATE ======================
if "discovery_df" not in st.session_state:
    st.session_state.discovery_df = None
if "selected_suburbs" not in st.session_state:
    st.session_state.selected_suburbs = set()

# ====================== CLIENT MODE ======================
client_mode = st.radio("Client Type", ("DSR Upload", "Explorer"), horizontal=True)

# ====================== STAGE 1 — DISCOVERY FILTERS ======================
st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences Only)")
st.caption("Soft filters only — no hard BUY gates applied yet.")

col1, col2 = st.columns(2)
with col1:
    selected_state = st.selectbox("State", ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"])
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
    renters_min, renters_max = st.slider("Renters Proportion (%)", 0, 40, (15, 35))
with col2:
    max_price = st.slider("Maximum Median Price ($)", 200_000, 2_000_000, 1_000_000, step=50_000)
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 8.0, 4.0)

# ====================== ENGINE LOGIC (from your engine.py) ======================
def normalise_percent(val):
    if pd.isna(val):
        return None
    try:
        val = float(str(val).replace("%", "").strip())
        return val * 100 if val <= 1 else val
    except:
        return None

def normalise_plain(val):
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None

def evaluate_buy_gates(factors):
    failed_gates = []
    if factors.get("renters_pct") is None or not (15 <= factors["renters_pct"] <= 35):
        failed_gates.append("Renters %")
    if factors.get("vacancy_pct") is None or factors["vacancy_pct"] >= 2:
        failed_gates.append("Vacancy")
    if factors.get("demand_supply_ratio") is None or factors["demand_supply_ratio"] <= 55:
        failed_gates.append("Demand / Supply")
    if factors.get("stock_on_market_pct") is None or factors["stock_on_market_pct"] >= 1.3:
        failed_gates.append("Stock on Market")
    if factors.get("gross_rental_yield") is None or factors["gross_rental_yield"] <= 4:
        failed_gates.append("Gross Yield")
    if factors.get("statistical_reliability") is None or factors["statistical_reliability"] <= 51:
        failed_gates.append("Reliability")
    decision = "BUY" if not failed_gates else "AVOID"
    return decision, failed_gates

def calculate_confidence(decision):
    score = 85 if decision == "BUY" else 60
    band = "High" if score >= 75 else "Medium"
    return score, band

# ====================== DSR UPLOAD MODE ======================
if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])
    if uploaded_file and st.button("Run Discovery (Filter Only)"):
        df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
        discovered = []
        for _, r in df.iterrows():
            if selected_state != "All" and r.get("State") != selected_state:
                continue
            dom = normalise_plain(str(r.get("Days on market", "")).replace("days", ""))
            renters = normalise_percent(r.get("Percent renters in market"))
            price = normalise_plain(r.get("Typical value")) or normalise_plain(r.get("Median 12 months"))
            yld = normalise_percent(r.get("Gross rental yield"))

            if dom is None or dom > max_dom: continue
            if renters is None or not (renters_min <= renters <= renters_max): continue
            if price is not None and price > max_price: continue
            if yld is None or yld < min_yield: continue

            discovered.append({
                "State": r.get("State"),
                "Suburb": r.get("Suburb"),
                "Median Price": price,
                "Days on Market": dom,
                "row": r
            })
        st.session_state.discovery_df = pd.DataFrame(discovered)
        st.session_state.selected_suburbs = set(st.session_state.discovery_df["Suburb"])

# ====================== EXPLORER MODE (Demo) ======================
if client_mode == "Explorer":
    if st.button("Run Discovery (Filter Only)"):
        demo_data = [
            {"State": "NSW", "Suburb": "Grafton", "Median Price": 520000, "Days on Market": 39, "row": {"Percent renters in market": 0.352, "Vacancy rate": 0.0038, "Demand to Supply Ratio": 59, "Percent stock on market": 0.0083, "Gross rental yield": 0.0534, "Statistical reliability": 70}},
            {"State": "QLD", "Suburb": "Norville", "Median Price": 570000, "Days on Market": 43, "row": {"Percent renters in market": 0.31, "Vacancy rate": 0.0057, "Demand to Supply Ratio": 58, "Percent stock on market": 0.0048, "Gross rental yield": 0.0508, "Statistical reliability": 54}},
        ]
        st.session_state.discovery_df = pd.DataFrame(demo_data)
        st.session_state.selected_suburbs = set(st.session_state.discovery_df["Suburb"])

# ====================== STAGE 1 RESULTS ======================
if st.session_state.discovery_df is not None and not st.session_state.discovery_df.empty:
    st.markdown("## 📍 Discovery Results")
    st.dataframe(st.session_state.discovery_df[["State", "Suburb", "Median Price", "Days on Market"]], use_container_width=True)

    st.session_state.selected_suburbs = set()
    for _, row in st.session_state.discovery_df.iterrows():
        if st.checkbox(row["Suburb"], True):
            st.session_state.selected_suburbs.add(row["Suburb"])

# ====================== STAGE 2 — DEEP ANALYSIS ======================
if st.session_state.selected_suburbs:
    st.markdown("## 🟥 Stage 2 — Deep Analysis (Hard BUY Gates)")
    col3, col4 = st.columns(2)
    with col3:
        max_vacancy = st.slider("Maximum Vacancy (%)", 0.0, 5.0, 2.0)
        max_stock = st.slider("Maximum Stock on Market (%)", 0.0, 3.0, 1.3)
    with col4:
        min_dsr = st.slider("Minimum Demand / Supply Ratio", 40, 80, 55)

    if st.button("Run Deep Analysis on Selected Suburbs"):
        results = []
        for _, r in st.session_state.discovery_df.iterrows():
            if r["Suburb"] not in st.session_state.selected_suburbs:
                continue

            factors = {
                "renters_pct": normalise_percent(r["row"].get("Percent renters in market")),
                "vacancy_pct": normalise_plain(r["row"].get("Vacancy rate")),
                "demand_supply_ratio": normalise_plain(r["row"].get("Demand to Supply Ratio")),
                "stock_on_market_pct": normalise_plain(r["row"].get("Percent stock on market")),
                "gross_rental_yield": normalise_percent(r["row"].get("Gross rental yield")),
                "statistical_reliability": normalise_plain(r["row"].get("Statistical reliability")),
            }

            decision, failed_gates = evaluate_buy_gates(factors)
            confidence_score, confidence_band = calculate_confidence(decision)

            results.append({
                "Suburb": r["Suburb"],
                "Decision": decision,
                "Confidence": confidence_band,
                "Confidence Score": confidence_score,
                "Failed Gates": ", ".join(failed_gates) if failed_gates else "None"
            })

        st.subheader("✅ Deep Analysis Results")
        st.dataframe(pd.DataFrame(results), use_container_width=True)

st.caption("Property Investment Accelerator — Authoritative Logic Engine")
