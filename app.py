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
if "stage1_results" not in st.session_state:
    st.session_state.stage1_results = None

if "client_mode" not in st.session_state:
    st.session_state.client_mode = "Explorer"

# ============================================================
# CLIENT TYPE SELECTION
# ============================================================
st.markdown("### Choose how you want to use the Accelerator")

client_mode = st.radio(
    "Client Type",
    ("DSR Upload", "Explorer"),
    index=0 if st.session_state.client_mode == "DSR Upload" else 1
)

st.session_state.client_mode = client_mode

# ============================================================
# SHARED FILTERS (DISCOVERY ONLY)
# ============================================================
st.markdown("### Stage 1 — Discovery Filters (Preferences)")
st.caption("Filters narrow the universe. No investment logic applied yet.")

col1, col2 = st.columns(2)

with col1:
    selected_state = st.selectbox("State", ["All", "NSW", "VIC", "QLD", "TAS", "NT"])
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
    renters_min, renters_max = st.slider("Renters Proportion (%)", 0, 40, (15, 35))

with col2:
    max_price = st.slider("Maximum Median Price ($)", 200_000, 2_000_000, 1_000_000, step=50_000)
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 8.0, 4.0)

# ============================================================
# HELPERS
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

# ============================================================
# CLIENT 1 — DSR UPLOAD (TWO‑STAGE)
# ============================================================
if client_mode == "DSR Upload":

    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("✅ DSR uploaded")

        # ---------- STAGE 1: DISCOVERY ----------
        if st.button("Run Discovery (Filter Only)"):

            discovery = []

            for _, r in df.iterrows():

                if selected_state != "All" and r.get("State") != selected_state:
                    continue

                dom = safe_int(r.get("Days on market"))
                renters = pct(r.get("Percent renters in market"))
                yield_ = pct(r.get("Gross rental yield"))
                price = r.get("Median price")

                if dom is None or dom > max_dom:
                    continue
                if renters is None or not (renters_min <= renters <= renters_max):
                    continue
                if yield_ is None or yield_ < min_yield:
                    continue
                if price is not None and price > max_price:
                    continue

                discovery.append(r)

            st.session_state.stage1_results = discovery

            st.subheader("📍 Discovery Results")
            if discovery:
                st.dataframe(
                    pd.DataFrame(discovery)[["State", "Suburb", "Median price", "Days on market"]],
                    use_container_width=True
                )
            else:
                st.warning("No suburbs matched your discovery filters.")

        # ---------- STAGE 2: DEEP ANALYSIS ----------
        if st.session_state.stage1_results and st.button("Run Deep Analysis"):

            analysis = []

            for r in st.session_state.stage1_results:

                factors = {
                    "renters_pct": pct(r.get("Percent renters in market")),
                    "vacancy_pct": pct(r.get("Vacancy rate")),
                    "demand_supply_ratio": r.get("Demand to Supply Ratio"),
                    "stock_on_market_pct": pct(r.get("Percent stock on market")),
                    "gross_rental_yield": pct(r.get("Gross rental yield")),
                    "statistical_reliability": r.get("Statistical reliability"),
                }

                decision, failed = evaluate_buy_gates(factors)
                _, band = calculate_confidence(decision)

                analysis.append({
                    "State": r.get("State"),
                    "Suburb": r.get("Suburb"),
                    "Decision": decision,
                    "Confidence": band,
                    "Failed Gates": ", ".join(failed) if failed else "None"
                })

            st.subheader("✅ Deep Analysis Results")
            st.dataframe(pd.DataFrame(analysis), use_container_width=True)

# ============================================================
# CLIENT 2 — EXPLORER (TWO‑STAGE)
# ============================================================
if client_mode == "Explorer":

    STATE_SUBURBS = {
        "NSW": ["Cessnock", "Maitland", "Tamworth"],
        "VIC": ["Ballarat", "Bendigo"],
        "QLD": ["Toowoomba", "Mackay"],
    }

    state = selected_state if selected_state != "All" else st.selectbox("State", STATE_SUBURBS.keys())

    suburbs = STATE_SUBURBS[state]

    # ---------- STAGE 1: DISCOVERY ----------
    if st.button("Run Discovery (Filter Only)"):

        discovery = []

        for suburb in suburbs:
            dom = random.randint(20, 150)
            renters = random.uniform(10, 45)
            price = random.randint(300_000, 1_600_000)
            yield_ = random.uniform(3.0, 7.5)

            if dom > max_dom:
                continue
            if not (renters_min <= renters <= renters_max):
                continue
            if yield_ < min_yield:
                continue
            if price > max_price:
                continue

            discovery.append({
                "State": state,
                "Suburb": suburb,
                "Median Price": price,
                "Days on Market": dom,
            })

        st.session_state.stage1_results = discovery

        st.subheader("📍 Discovery Results")
        if discovery:
            st.dataframe(pd.DataFrame(discovery), use_container_width=True)
        else:
            st.warning("No suburbs matched your discovery filters.")

    # ---------- STAGE 2: DEEP ANALYSIS ----------
    if st.session_state.stage1_results and st.button("Run Deep Analysis"):

        analysis = []

        for r in st.session_state.stage1_results:

            factors = {
                "renters_pct": random.uniform(15, 35),
                "vacancy_pct": random.uniform(0.5, 3.0),
                "demand_supply_ratio": random.uniform(50, 75),
                "stock_on_market_pct": random.uniform(0.5, 2.0),
                "gross_rental_yield": random.uniform(4.0, 7.0),
                "statistical_reliability": random.uniform(50, 85),
            }

            decision, failed = evaluate_buy_gates(factors)
            _, band = calculate_confidence(decision)

            analysis.append({
                "State": r["State"],
                "Suburb": r["Suburb"],
                "Decision": decision,
                "Confidence": band,
                "Failed Gates": ", ".join(failed) if failed else "None"
            })

        st.subheader("✅ Deep Analysis Results")
        st.dataframe(pd.DataFrame(analysis), use_container_width=True)
