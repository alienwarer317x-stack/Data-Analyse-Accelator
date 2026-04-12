import streamlit as st
import pandas as pd
import random

from engine import evaluate_buy_gates, calculate_confidence

# ============================================================
# APP SETUP
# ============================================================
st.set_page_config(page_title="Property Investment Accelerator", layout="wide")

st.title("🏠 Property Investment Accelerator")
st.subheader("Authoritative Logic Engine · Two‑Stage Discovery & Analysis")

# ============================================================
# SESSION STATE
# ============================================================
if "discovery_df" not in st.session_state:
    st.session_state.discovery_df = None

if "selected_suburbs" not in st.session_state:
    st.session_state.selected_suburbs = set()

# ============================================================
# CLIENT TYPE SELECTION
# ============================================================
st.markdown("### Choose how you want to use the Accelerator")

client_mode = st.radio(
    "Client Type",
    ("DSR Upload", "Explorer"),
)

# ============================================================
# STAGE 1 — DISCOVERY FILTERS (PREFERENCES ONLY)
# ============================================================
st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences)")
st.caption("These filters narrow the universe only. No investment logic is applied.")

col1, col2 = st.columns(2)

with col1:
    selected_state = st.selectbox("State", ["All", "NSW", "VIC", "QLD", "TAS", "NT"])
    property_type = st.radio("Property Type", ["House", "Unit", "Both"], horizontal=True)
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
    renters_min, renters_max = st.slider("Renters Proportion (%)", 0, 40, (15, 35))

with col2:
    max_price = st.slider(
        "Maximum Median Price ($)",
        200_000, 2_000_000, 1_000_000, step=50_000
    )
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 8.0, 4.0)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def pct(val):
    try:
        v = float(val)
        return v * 100 if v <= 1 else v
    except:
        return None

def safe_int(val):
    try:
        return int(float(val))
    except:
        return None

def pick_price(row):
    if property_type == "House":
        return row.get("Median house price") or row.get("Median price")
    if property_type == "Unit":
        return row.get("Median unit price") or row.get("Median price")
    return (
        row.get("Median house price")
        or row.get("Median unit price")
        or row.get("Median price")
    )

def pick_yield(row):
    if property_type == "House":
        return pct(row.get("Gross house rental yield") or row.get("Gross rental yield"))
    if property_type == "Unit":
        return pct(row.get("Gross unit rental yield") or row.get("Gross rental yield"))
    return pct(row.get("Gross rental yield"))

# ============================================================
# CLIENT 1 — DSR UPLOAD
# ============================================================
if client_mode == "DSR Upload":

    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded_file and st.button("Run Discovery (Filter Only)"):

        df = pd.read_excel(uploaded_file)
        discovered = []

        for _, r in df.iterrows():
            if selected_state != "All" and r.get("State") != selected_state:
                continue

            dom = safe_int(r.get("Days on market"))
            renters = pct(r.get("Percent renters in market"))
            price = pick_price(r)
            yld = pick_yield(r)

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
                "row": r
            })

        st.session_state.discovery_df = pd.DataFrame(discovered)
        st.session_state.selected_suburbs = set(st.session_state.discovery_df["Suburb"])

# ============================================================
# CLIENT 2 — EXPLORER
# ============================================================
if client_mode == "Explorer":

    STATE_SUBURBS = {
        "NSW": ["Cessnock", "Maitland", "Kurri Kurri", "Singleton"],
        "VIC": ["Ballarat", "Bendigo"],
        "QLD": ["Toowoomba", "Mackay"],
    }

    state = selected_state if selected_state != "All" else st.selectbox("State", STATE_SUBURBS.keys())

    if st.button("Run Discovery (Filter Only)"):

        discovered = []

        for suburb in STATE_SUBURBS[state]:
            dom = random.randint(20, 150)
            renters = random.uniform(10, 45)
            price = random.randint(300_000, 1_600_000)
            yld = random.uniform(3.0, 7.5)

            if dom > max_dom:
                continue
            if not (renters_min <= renters <= renters_max):
                continue
            if price > max_price:
                continue
            if yld < min_yield:
                continue

            discovered.append({
                "State": state,
                "Suburb": suburb,
                "Median Price": price,
                "Days on Market": dom,
                "row": {
                    "renters_pct": renters,
                    "vacancy_pct": random.uniform(0.5, 3.0),
                    "demand_supply_ratio": random.uniform(55, 75),
                    "stock_on_market_pct": random.uniform(0.5, 2.0),
                    "gross_rental_yield": yld,
                    "statistical_reliability": random.uniform(50, 85),
                }
            })

        st.session_state.discovery_df = pd.DataFrame(discovered)
        st.session_state.selected_suburbs = set(st.session_state.discovery_df["Suburb"])

# ============================================================
# STAGE 1 — DISCOVERY RESULTS + SELECTION
# ============================================================
if st.session_state.discovery_df is not None and not st.session_state.discovery_df.empty:

    st.markdown("## 📍 Discovery Results")

    select_all = st.checkbox("Select all suburbs for Deep Analysis", True)

    if select_all:
        st.session_state.selected_suburbs = set(st.session_state.discovery_df["Suburb"])
    else:
        st.session_state.selected_suburbs.clear()

    for _, row in st.session_state.discovery_df.iterrows():
        suburb = row["Suburb"]
        checked = suburb in st.session_state.selected_suburbs
        if st.checkbox(suburb, checked):
            st.session_state.selected_suburbs.add(suburb)
        else:
            st.session_state.selected_suburbs.discard(suburb)

    st.dataframe(
        st.session_state.discovery_df[["State", "Suburb", "Median Price", "Days on Market"]],
        use_container_width=True
    )

# ============================================================
# STAGE 2 — DEEP ANALYSIS FILTERS
# ============================================================
if st.session_state.selected_suburbs:

    st.markdown("## 🟥 Stage 2 — Deep Analysis Filters")

    col3, col4 = st.columns(2)

    with col3:
        max_vacancy = st.slider("Maximum Vacancy (%)", 0.0, 5.0, 2.0)
        max_stock = st.slider("Maximum Stock on Market (%)", 0.0, 3.0, 1.3)

    with col4:
        min_dsr = st.slider("Minimum Demand / Supply", 40, 80, 55)

    if st.button("Run Deep Analysis on Selected Suburbs"):

        results = []

        for _, r in st.session_state.discovery_df.iterrows():
            if r["Suburb"] not in st.session_state.selected_suburbs:
                continue

            factors = (
                r["row"] if client_mode == "Explorer"
                else {
                    "renters_pct": pct(r["row"].get("Percent renters in market")),
                    "vacancy_pct": pct(r["row"].get("Vacancy rate")),
                    "demand_supply_ratio": r["row"].get("Demand to Supply Ratio"),
                    "stock_on_market_pct": pct(r["row"].get("Percent stock on market")),
                    "gross_rental_yield": pick_yield(r["row"]),
                    "statistical_reliability": r["row"].get("Statistical reliability"),
                }
            )

            if factors["vacancy_pct"] > max_vacancy:
                continue
            if factors["stock_on_market_pct"] > max_stock:
                continue
            if factors["demand_supply_ratio"] < min_dsr:
                continue

            decision, failed = evaluate_buy_gates(factors)
            score, band = calculate_confidence(decision)

            results.append({
                "State": r["State"],
                "Suburb": r["Suburb"],
                "Decision": decision,
                "Confidence": band,
                "Failed Gates": ", ".join(failed) if failed else "None",
            })

        st.subheader("✅ Deep Analysis Results")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
