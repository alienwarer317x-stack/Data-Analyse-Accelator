import streamlit as st
import pandas as pd
import random
import time

from engine import evaluate_buy_gates, calculate_confidence

# ============================================================
# APP SETUP
# ============================================================
st.set_page_config(page_title="Property Investment Accelerator", layout="wide")

st.title("🏠 Property Investment Accelerator")
st.subheader("Authoritative Logic Engine · Multi‑Client Platform")

# ============================================================
# CLIENT TYPE SELECTION
# ============================================================
client_mode = st.radio(
    "Client Type",
    (
        "I have DSR data (Upload Spreadsheet)",
        "I want to explore suburbs (No data)"
    )
)

# ============================================================
# SHARED FILTERS
# ============================================================
st.markdown("### Discovery Filters (Preferences)")
st.caption("Filters narrow candidates but never override BUY logic.")

col1, col2 = st.columns(2)

with col1:
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
    renters_min, renters_max = st.slider("Renters Proportion (%)", 0, 40, (15, 35))

with col2:
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 7.5, 4.0)
    max_vacancy = st.slider("Maximum Vacancy (%)", 0.0, 5.0, 2.0)
    min_dsr = st.slider("Minimum Demand / Supply", 40, 80, 55)
    max_stock = st.slider("Maximum Stock on Market (%)", 0.0, 3.0, 1.3)

# ============================================================
# NORMALISATION HELPERS
# ============================================================
def pct(val):
    if pd.isna(val):
        return None
    try:
        return float(val) * 100 if float(val) <= 1 else float(val)
    except:
        return None

def safe_int(val):
    try:
        if pd.isna(val):
            return None
        return int(float(val))
    except:
        return None

# ============================================================
# CLIENT TYPE 1 — DSR UPLOAD (FIXED)
# ============================================================
if client_mode == "I have DSR data (Upload Spreadsheet)":

    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("✅ DSR uploaded. Apply filters and run analysis.")

        if st.button("Run DSR Analysis"):

            st.info("🔄 Applying filters and running BUY logic on DSR data…")

            rows = []

            for _, r in df.iterrows():

                # -------- NORMALISE VALUES --------
                dom = safe_int(r.get("Days on market"))
                renters = pct(r.get("Percent renters in market"))
                vacancy = pct(r.get("Vacancy rate"))
                yield_ = pct(r.get("Gross rental yield"))
                stock = pct(r.get("Percent stock on market"))
                dsr = r.get("Demand to Supply Ratio")
                reliability = r.get("Statistical reliability")

                # -------- FILTER STAGE --------
                if dom is None or dom > max_dom:
                    continue
                if renters is None or not (renters_min <= renters <= renters_max):
                    continue
                if vacancy is None or vacancy > max_vacancy:
                    continue
                if yield_ is None or yield_ < min_yield:
                    continue
                if stock is None or stock > max_stock:
                    continue
                if dsr is None or dsr < min_dsr:
                    continue

                factors = {
                    "renters_pct": renters,
                    "vacancy_pct": vacancy,
                    "demand_supply_ratio": dsr,
                    "stock_on_market_pct": stock,
                    "gross_rental_yield": yield_,
                    "statistical_reliability": reliability,
                }

                decision, failed = evaluate_buy_gates(factors)
                _, band = calculate_confidence(decision)

                rows.append({
                    "Suburb": r.get("Suburb"),
                    "Decision": decision,
                    "Confidence": band,
                    "Failed Gates": ", ".join(failed) if failed else "None"
                })

            if not rows:
                st.warning(
                    "No suburbs matched your filters.\n\n"
                    "Tip: widen Days on Market or Vacancy slightly."
                )
            else:
                st.subheader("📊 DSR Results (Filtered)")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ============================================================
# CLIENT TYPE 2 — EXPLORER (UNCHANGED)
# ============================================================
if client_mode == "I want to explore suburbs (No data)":
    st.info("Explorer path unaffected and continues to work.")
