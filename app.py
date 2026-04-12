import streamlit as st
import pandas as pd
from io import BytesIO
from engine import evaluate_buy_gates, calculate_confidence

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two‑Stage Discovery + Authoritative Logic Engine")

# ====================== SESSION STATE ======================
if "discovery_df" not in st.session_state:
    st.session_state.discovery_df = None
if "selected_suburbs" not in st.session_state:
    st.session_state.selected_suburbs = set()

# ====================== CLIENT MODE ======================
client_mode = st.radio("Client Type", ("DSR Upload", "Explorer"), horizontal=True)

# ====================== STAGE 1 — DISCOVERY FILTERS ======================
st.markdown("## 🟩 Stage 1 — Discovery Filters (Client Preferences Only)")
st.caption("Soft filters only. No investment logic or BUY gates applied here.")

col1, col2 = st.columns(2)
with col1:
    selected_state = st.selectbox("State", ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"])
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
with col2:
    max_price = st.slider("Maximum Median Price ($)", 200_000, 2_000_000, 1_000_000, step=50_000)
    min_yield = st.slider("Minimum Gross Rental Yield (%)", 3.0, 8.0, 4.0)   # ← Yield added back

# ====================== NORMALISATION HELPERS ======================
def normalise_plain(val):
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None

def normalise_percent(val):
    if pd.isna(val):
        return None
    try:
        v = float(str(val).replace("%", "").strip())
        return v * 100 if v <= 1 else v
    except:
        return None

# ====================== DSR UPLOAD MODE ======================
if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])
    if uploaded_file and st.button("Apply Discovery Filters"):
        df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
        discovered = []
        for _, r in df.iterrows():
            if selected_state != "All" and r.get("State") != selected_state:
                continue

            dom = normalise_plain(str(r.get("Days on market", "")).replace("days", ""))
            price = normalise_plain(r.get("Typical value")) or normalise_plain(r.get("Median 12 months"))
            yld = normalise_percent(r.get("Gross rental yield"))

            # STAGE 1 FILTERS ONLY (client preferences)
            if dom is None or dom > max_dom:
                continue
            if price is not None and price > max_price:
                continue
            if yld is None or yld < min_yield:          # ← Yield filter active
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
            st.warning("⚠️ No suburbs matched your discovery filters.")
        else:
            st.session_state.selected_suburbs = set(st.session_state.discovery_df["Suburb"])

# ====================== EXPLORER MODE ======================
if client_mode == "Explorer" and st.button("Apply Discovery Filters"):
    demo_data = [
        {"State": "NSW", "Suburb": "Grafton", "Median Price": 520000, "Days on Market": 39, "_row": {"Gross rental yield": 0.0534}},
        {"State": "QLD", "Suburb": "Norville", "Median Price": 570000, "Days on Market": 43, "_row": {"Gross rental yield": 0.0508}},
    ]
    df = pd.DataFrame(demo_data)
    df = df[(df["Median Price"] <= max_price) & (df["Days on Market"] <= max_dom)]
    st.session_state.discovery_df = df
    st.session_state.selected_suburbs = set(df["Suburb"])

# ====================== STAGE 1 RESULTS ======================
if st.session_state.discovery_df is not None and not st.session_state.discovery_df.empty:
    st.markdown("## 📍 Discovery Results")
    st.dataframe(st.session_state.discovery_df[["State", "Suburb", "Median Price", "Days on Market"]], use_container_width=True)

    st.session_state.selected_suburbs = set()
    for idx, row in st.session_state.discovery_df.iterrows():
        suburb = row["Suburb"]
        if st.checkbox(suburb, True, key=f"disc_{idx}_{suburb}"):
            st.session_state.selected_suburbs.add(suburb)

# ====================== STAGE 2 — DEEP ANALYSIS ======================
if st.session_state.selected_suburbs:
    st.markdown("## 🟥 Stage 2 — Deep Analysis (Authoritative Engine Only)")
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
