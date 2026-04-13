import streamlit as st
import pandas as pd
from io import BytesIO
from engine import evaluate_buy_gates, calculate_confidence

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two‑Stage Discovery + Authoritative Logic Engine")

# ====================== SESSION STATE ======================
if "dsr_discovery_df" not in st.session_state:
    st.session_state.dsr_discovery_df = None
if "explorer_df" not in st.session_state:
    st.session_state.explorer_df = None

client_mode = st.radio("Client Type", ("DSR Upload", "Explorer"), horizontal=True)

st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences Only)")
state = st.selectbox("State", ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"])
max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
max_price = st.slider("Maximum Median Price ($)", 200_000, 2_000_000, 1_000_000, step=50_000)
min_yield = st.slider("Minimum Gross Rental Yield (%)", 3.0, 8.0, 4.0)

# ====================== NORMALISATION HELPERS (from engine) ======================
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
    uploaded_file = st.file_uploader("Upload DSR Excel", type="xlsx")
    if uploaded_file is not None:
        st.session_state.dsr_discovery_df = pd.read_excel(uploaded_file)
        current_df = st.session_state.dsr_discovery_df
    else:
        current_df = pd.DataFrame()
else:
    if st.session_state.explorer_df is None:
        st.error("Explorer data not available. Please use DSR Upload.")
        st.stop()
    current_df = st.session_state.explorer_df

# Discovery Results
if not current_df.empty:
    st.markdown(f"## 📍 Discovery Results ({len(current_df)} suburbs)")

    df_display = current_df.copy()
    if "Median 12 months" in df_display.columns:
        df_display["Median Price"] = df_display["Median 12 months"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")

    st.dataframe(df_display[["State", "Suburb", "Median Price", "Days on Market"]], use_container_width=True)

    all_suburbs = current_df["Suburb"].tolist()
    selected_suburbs = st.multiselect("Select for Stage 2", options=all_suburbs)
else:
    st.info("Adjust filters above and click Apply Discovery Filters.")
    selected_suburbs = []

# Stage 2 — Engine Evaluation
if selected_suburbs:
    st.markdown("## 🟥 Stage 2 — Engine Evaluation")
    for suburb in selected_suburbs:
        suburb_row = current_df[current_df["Suburb"] == suburb].iloc[0]
       
        # Prepare factors for engine
        row = suburb_row.to_dict() if hasattr(suburb_row, "to_dict") else suburb_row
        factors = {
            "renters_pct": normalise_percent(row.get("Percent renters in market")),
            "vacancy_pct": normalise_plain(row.get("Vacancy rate")),
            "demand_supply_ratio": normalise_plain(row.get("Demand to Supply Ratio")),
            "stock_on_market_pct": normalise_plain(row.get("Percent stock on market")),
            "gross_rental_yield": normalise_percent(row.get("Gross rental yield")),
            "statistical_reliability": normalise_plain(row.get("Statistical reliability")),
        }

        with st.expander(f"🔍 {suburb}"):
            decision, failed = evaluate_buy_gates(factors)
            score, band = calculate_confidence(decision)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Decision", decision)
                st.metric("Confidence Score", score)
                st.metric("Confidence", band)
            with col2:
                st.write("**Failed Gates:**", failed if failed else "None")

st.caption("Property Investment Accelerator — Authoritative Logic Engine")
