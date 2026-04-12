import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two‑Stage Discovery + Authoritative Logic Engine")

# ====================== SESSION STATE ======================
if "discovery_df" not in st.session_state:
    st.session_state.discovery_df = None

if "selected_suburbs" not in st.session_state:
    st.session_state.selected_suburbs = set()

# ====================== CLIENT MODE ======================
client_mode = st.radio(
    "Client Type",
    ("DSR Upload", "Explorer"),
    horizontal=True
)

# ====================== STAGE 1 — DISCOVERY FILTERS ======================
st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences Only)")
st.caption("Soft filters only — no hard BUY gates applied yet.")

col1, col2 = st.columns(2)

with col1:
    selected_state = st.selectbox(
        "State", ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"]
    )
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
    renters_min, renters_max = st.slider(
        "Renters Proportion (%)", 0, 40, (15, 35)
    )

with col2:
    max_price = st.slider(
        "Maximum Median Price ($)",
        200_000, 2_000_000, 1_000_000, step=50_000
    )
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 8.0, 4.0)

# ====================== ENGINE HELPERS ======================
def normalise_percent(val):
    if pd.isna(val):
        return None
    try:
        v = float(str(val).replace("%", "").strip())
        return v * 100 if v <= 1 else v
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
    failed = []

    if factors["renters_pct"] is None or not (15 <= factors["renters_pct"] <= 35):
        failed.append("Renters %")
    if factors["vacancy_pct"] is None or factors["vacancy_pct"] >= 2:
        failed.append("Vacancy")
    if factors["demand_supply_ratio"] is None or factors["demand_supply_ratio"] <= 55:
        failed.append("Demand / Supply")
    if factors["stock_on_market_pct"] is None or factors["stock_on_market_pct"] >= 1.3:
        failed.append("Stock on Market")
    if factors["gross_rental_yield"] is None or factors["gross_rental_yield"] <= 4:
        failed.append("Gross Yield")
    if factors["statistical_reliability"] is None or factors["statistical_reliability"] <= 51:
        failed.append("Reliability")

    return ("BUY" if not failed else "AVOID", failed)

def calculate_confidence(decision):
    score = 85 if decision == "BUY" else 60
    return score, ("High" if score >= 75 else "Medium")

# ====================== DSR MODE ======================
if client_mode == "DSR Upload":
    uploaded = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded and st.button("Apply Discovery Filters"):
        df = pd.read_excel(uploaded)

        discovered = []

        for _, r in df.iterrows():
            if selected_state != "All" and r.get("State") != selected_state:
                continue

            dom = normalise_plain(r.get("Days on market"))
            renters = normalise_percent(r.get("Percent renters in market"))
            price = normalise_plain(r.get("Typical value")) or normalise_plain(r.get("Median 12 months"))
            yld = normalise_percent(r.get("Gross rental yield"))

            if dom is None or dom > max_dom:
                continue
            if renters is None or not (renters_min <= renters <= renters_max):
                continue
            if price is not None and price > max_price:
                continue
            if yld is None or yld < min_yield:
                continue

            discovered.append({
                "State": r.get("State"),
                "Suburb": r.get("Suburb"),
                "Median Price": price,
                "Days on Market": dom,
                "_row": r
            })

        st.session_state.discovery_df = pd.DataFrame(discovered)

        if st.session_state.discovery_df.empty:
            st.session_state.selected_suburbs.clear()
            st.warning(
                "⚠️ No suburbs matched your discovery filters.\n\n"
                "Try widening price, days on market, renters %, or yield."
            )
        else:
            st.session_state.selected_suburbs = set(
                st.session_state.discovery_df["Suburb"]
            )

# ====================== EXPLORER MODE ======================
if client_mode == "Explorer" and st.button("Apply Discovery Filters"):
    demo = [
        {
            "State": "NSW",
            "Suburb": "Grafton",
            "Median Price": 520000,
            "Days on Market": 39,
            "_row": {
                "Percent renters in market": 0.352,
                "Vacancy rate": 0.0038,
                "Demand to Supply Ratio": 59,
                "Percent stock on market": 0.0083,
                "Gross rental yield": 0.0534,
                "Statistical reliability": 70
            }
        },
        {
            "State": "QLD",
            "Suburb": "Norville",
            "Median Price": 570000,
            "Days on Market": 43,
            "_row": {
                "Percent renters in market": 0.31,
                "Vacancy rate": 0.0057,
                "Demand to Supply Ratio": 58,
                "Percent stock on market": 0.0048,
                "Gross rental yield": 0.0508,
                "Statistical reliability": 54
            }
        },
    ]

    df = pd.DataFrame(demo)

    df = df[
        (df["Median Price"] <= max_price) &
        (df["Days on Market"] <= max_dom)
    ]

    st.session_state.discovery_df = df
    st.session_state.selected_suburbs = set(df["Suburb"])

# ====================== STAGE 1 RESULTS ======================
if st.session_state.discovery_df is not None and not st.session_state.discovery_df.empty:
    st.markdown("## 📍 Discovery Results")

    select_all = st.checkbox("Select all suburbs for Deep Analysis", True)

    if select_all:
        st.session_state.selected_suburbs = set(st.session_state.discovery_df["Suburb"])

    for suburb in st.session_state.discovery_df["Suburb"]:
        checked = suburb in st.session_state.selected_suburbs
        if st.checkbox(suburb, checked, key=f"disc_{suburb}"):
            st.session_state.selected_suburbs.add(suburb)
        else:
            st.session_state.selected_suburbs.discard(suburb)

    st.dataframe(
        st.session_state.discovery_df[["State", "Suburb", "Median Price", "Days on Market"]],
        use_container_width=True
    )

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

            row = r["_row"]

            factors = {
                "renters_pct": normalise_percent(row.get("Percent renters in market")),
                "vacancy_pct": normalise_plain(row.get("Vacancy rate")),
                "demand_supply_ratio": normalise_plain(row.get("Demand to Supply Ratio")),
                "stock_on_market_pct": normalise_plain(row.get("Percent stock on market")),
                "gross_rental_yield": normalise_percent(row.get("Gross rental yield")),
                "statistical_reliability": normalise_plain(row.get("Statistical reliability")),
            }

            decision, failed = evaluate_buy_gates(factors)
            score, band = calculate_confidence(decision)

            results.append({
                "Suburb": r["Suburb"],
                "Decision": decision,
                "Confidence": band,
                "Confidence Score": score,
                "Failed Gates": ", ".join(failed) if failed else "None"
            })

        st.subheader("✅ Deep Analysis Results")
        st.dataframe(pd.DataFrame(results), use_container_width=True)

st.caption("Property Investment Accelerator — Authoritative Logic Engine")
