import streamlit as st
import pandas as pd

from engine import evaluate_buy_gates, calculate_confidence

# ============================================================
# APP SETUP
# ============================================================
st.set_page_config(page_title="Property Investment Accelerator", layout="wide")

st.title("🏠 Property Investment Accelerator")
st.subheader("Authoritative Logic Engine · Multi‑Client Platform")

# ============================================================
# SESSION STATE INITIALISATION
# ============================================================
if "client_mode" not in st.session_state:
    st.session_state.client_mode = "I want to explore suburbs (No data)"

# ============================================================
# CLIENT TYPE SELECTION
# ============================================================
st.markdown("### Choose how you want to use the Accelerator")

client_mode = st.radio(
    "Client Type",
    (
        "I have DSR data (Upload Spreadsheet)",
        "I want to explore suburbs (No data)",
    ),
    index=0 if st.session_state.client_mode == "I have DSR data (Upload Spreadsheet)" else 1,
)

st.session_state.client_mode = client_mode

# ============================================================
# SHARED FILTERS (PREFERENCES)
# ============================================================
st.markdown("### Discovery Filters (Preferences)")
st.caption("Filters narrow candidates but never override BUY logic.")

col1, col2 = st.columns(2)

with col1:
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
    renters_min, renters_max = st.slider("Renters Proportion (%)", 0, 40, (15, 35))

with col2:
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 8.0, 4.0)
    max_vacancy = st.slider("Maximum Vacancy (%)", 0.0, 5.0, 2.0)

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

# ============================================================
# CLIENT TYPE 1 — DSR MODE (UPLOAD RENDERED ONLY HERE)
# ============================================================
if st.session_state.client_mode == "I have DSR data (Upload Spreadsheet)":

    uploaded_file = st.file_uploader(
        "Upload your DSR Excel file",
        type=["xlsx"],
        key="dsr_uploader"
    )

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("✅ DSR uploaded. Adjust filters and run analysis.")

        if st.button("Run DSR Analysis"):

            results = []

            for _, r in df.iterrows():
                dom = safe_int(r.get("Days on market"))
                renters = pct(r.get("Percent renters in market"))
                vacancy = pct(r.get("Vacancy rate"))
                yield_ = pct(r.get("Gross rental yield"))

                if dom is None or dom > max_dom:
                    continue
                if renters is None or not (renters_min <= renters <= renters_max):
                    continue
                if vacancy is None or vacancy > max_vacancy:
                    continue
                if yield_ is None or yield_ < min_yield:
                    continue

                factors = {
                    "renters_pct": renters,
                    "vacancy_pct": vacancy,
                    "demand_supply_ratio": r.get("Demand to Supply Ratio"),
                    "stock_on_market_pct": pct(r.get("Percent stock on market")),
                    "gross_rental_yield": yield_,
                    "statistical_reliability": r.get("Statistical reliability"),
                }

                decision, failed = evaluate_buy_gates(factors)
                _, band = calculate_confidence(decision)

                results.append({
                    "Suburb": r.get("Suburb"),
                    "Decision": decision,
                    "Confidence": band,
                    "Failed Gates": ", ".join(failed) if failed else "None",
                })

            if results:
                st.subheader("📊 DSR Results")
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.warning("No suburbs matched your filters.")

# ============================================================
# CLIENT TYPE 2 — EXPLORER MODE (NO UPLOAD SHOWN)
# ============================================================
if st.session_state.client_mode == "I want to explore suburbs (No data)":
    st.info("Explorer mode active. Upload is disabled by design.")
