import streamlit as st
import pandas as pd

from engine import evaluate_buy_gates, calculate_confidence

# ============================================================
# APP SETUP
# ============================================================
st.set_page_config(
    page_title="Property Investment Accelerator Matcher",
    layout="wide"
)

st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two‑Stage Discovery + Authoritative Logic Engine")

# ============================================================
# SESSION STATE
# ============================================================
if "discovery_df" not in st.session_state:
    st.session_state.discovery_df = None

if "selected_suburbs" not in st.session_state:
    st.session_state.selected_suburbs = set()

# ============================================================
# CLIENT MODE
# ============================================================
client_mode = st.radio(
    "Client Type",
    ("DSR Upload", "Explorer"),
    horizontal=True
)

# ============================================================
# STAGE 1 — DISCOVERY FILTERS (CLIENT ONLY)
# ============================================================
st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences Only)")
st.caption(
    "This stage applies only client preference ranges. "
    "No investment logic or BUY rules are applied."
)

col1, col2 = st.columns(2)

with col1:
    selected_state = st.selectbox(
        "State",
        ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"]
    )
    max_dom = st.slider(
        "Maximum Days on Market",
        0, 180, 90
    )

with col2:
    max_price = st.slider(
        "Maximum Median Price ($)",
        200_000, 2_000_000, 1_000_000, step=50_000
    )

# ============================================================
# RESET DISCOVERY
# ============================================================
if st.button("Reset Discovery Filters"):
    st.session_state.discovery_df = None
    st.session_state.selected_suburbs = set()

# ============================================================
# NORMALISATION HELPERS
# ============================================================
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

# ============================================================
# STAGE 1 — DISCOVERY (DSR UPLOAD)
# ============================================================
if client_mode == "DSR Upload":

    uploaded_file = st.file_uploader(
        "Upload your DSR Excel file",
        type=["xlsx"]
    )

    if uploaded_file and st.button("Apply Discovery Filters"):
        df = pd.read_excel(uploaded_file)

        discovered = []

        for _, r in df.iterrows():

            if selected_state != "All" and r.get("State") != selected_state:
                continue

            dom = normalise_plain(
                str(r.get("Days on market", "")).replace("days", "")
            )

            price = (
                normalise_plain(r.get("Typical value"))
                or normalise_plain(r.get("Median 12 months"))
            )

            # ---- STAGE 1: RANGE FILTERS ONLY ----
            if dom is None or dom > max_dom:
                continue
            if price is not None and price > max_price:
                continue

            discovered.append({
                "State": r.get("State"),
                "Suburb": r.get("Suburb"),
                "Median Price": price,
                "Days on Market": dom,
                "_row": r  # carry full row for Stage 2
            })

        st.session_state.discovery_df = pd.DataFrame(discovered)

        if st.session_state.discovery_df.empty:
            st.session_state.selected_suburbs.clear()
            st.warning(
                "⚠️ No suburbs matched your discovery filters.\n\n"
                "Try widening price or days‑on‑market ranges."
            )
        else:
            st.session_state.selected_suburbs = set(
                st.session_state.discovery_df["Suburb"]
            )

# ============================================================
# STAGE 1 — DISCOVERY (EXPLORER DEMO)
# ============================================================
if client_mode == "Explorer" and st.button("Apply Discovery Filters"):

    demo_data = [
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

    df = pd.DataFrame(demo_data)

    df = df[
        (df["Median Price"] <= max_price) &
        (df["Days on Market"] <= max_dom)
    ]

    st.session_state.discovery_df = df
    st.session_state.selected_suburbs = set(df["Suburb"])

# ============================================================
# STAGE 1 RESULTS + SELECTION
# ============================================================
if st.session_state.discovery_df is not None and not st.session_state.discovery_df.empty:

    st.markdown("## 📍 Discovery Results")

    select_all = st.checkbox(
        "Select all suburbs for Deep Analysis",
        True
    )

    if select_all:
        st.session_state.selected_suburbs = set(
            st.session_state.discovery_df["Suburb"]
        )

    for suburb in st.session_state.discovery_df["Suburb"]:
        checked = suburb in st.session_state.selected_suburbs
        if st.checkbox(suburb, checked, key=f"disc_{suburb}"):
            st.session_state.selected_suburbs.add(suburb)
        else:
            st.session_state.selected_suburbs.discard(suburb)

    st.dataframe(
        st.session_state.discovery_df[
            ["State", "Suburb", "Median Price", "Days on Market"]
        ],
        use_container_width=True
    )

# ============================================================
# STAGE 2 — DEEP ANALYSIS (ENGINE ONLY)
# ============================================================
if st.session_state.selected_suburbs:

    st.markdown("## 🟥 Stage 2 — Deep Analysis (Authoritative Engine)")

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
