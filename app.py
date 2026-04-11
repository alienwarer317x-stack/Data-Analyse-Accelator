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
# SHARED FILTERS (PREFERENCES)
# ============================================================
st.markdown("### Discovery Filters (Preferences)")
st.caption("Filters narrow candidates but never override BUY logic.")

col1, col2 = st.columns(2)

with col1:
    selected_state = st.selectbox("State", ["All", "NSW", "VIC", "QLD", "TAS", "NT"])
    property_type = st.radio("Property Type", ["House", "Unit", "Both"], horizontal=True)
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
    renters_min, renters_max = st.slider("Renters Proportion (%)", 0, 40, (15, 35))

with col2:
    max_price = st.slider("Maximum Median Price ($)", 200_000, 2_000_000, 1_000_000, step=50_000)
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 8.0, 4.0)
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
        v = float(val)
        return v * 100 if v <= 1 else v
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
# CLIENT 1 — DSR WITH FILTER DIAGNOSTICS
# ============================================================
if client_mode == "I have DSR data (Upload Spreadsheet)":

    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("✅ DSR uploaded. Apply filters and run analysis.")

        if st.button("Run DSR Analysis"):

            st.info("🔄 Applying filters and running BUY logic on DSR data…")

            rows = []

            # ---- DIAGNOSTIC COUNTERS ----
            diag = {
                "State": 0,
                "Property Type / Price": 0,
                "Days on Market": 0,
                "Renters Proportion": 0,
                "Vacancy": 0,
                "Gross Yield": 0,
                "Stock on Market": 0,
                "Demand / Supply": 0
            }

            for _, r in df.iterrows():

                # ---------- STATE ----------
                if selected_state != "All" and r.get("State") != selected_state:
                    diag["State"] += 1
                    continue

                # ---------- PROPERTY TYPE & PRICE ----------
                if property_type == "House":
                    price = r.get("Median house price")
                    gross_yield = pct(r.get("Gross house rental yield") or r.get("Gross rental yield"))
                elif property_type == "Unit":
                    price = r.get("Median unit price")
                    gross_yield = pct(r.get("Gross unit rental yield") or r.get("Gross rental yield"))
                else:
                    price = r.get("Median house price") or r.get("Median unit price")
                    gross_yield = pct(r.get("Gross rental yield"))

                if price is None or price > max_price:
                    diag["Property Type / Price"] += 1
                    continue

                # ---------- NORMALISE ----------
                dom = safe_int(r.get("Days on market"))
                renters = pct(r.get("Percent renters in market"))
                vacancy = pct(r.get("Vacancy rate"))
                stock = pct(r.get("Percent stock on market"))
                dsr = r.get("Demand to Supply Ratio")
                reliability = r.get("Statistical reliability")

                # ---------- FILTERS ----------
                if dom is None or dom > max_dom:
                    diag["Days on Market"] += 1
                    continue
                if renters is None or not (renters_min <= renters <= renters_max):
                    diag["Renters Proportion"] += 1
                    continue
                if vacancy is None or vacancy > max_vacancy:
                    diag["Vacancy"] += 1
                    continue
                if gross_yield is None or gross_yield < min_yield:
                    diag["Gross Yield"] += 1
                    continue
                if stock is None or stock > max_stock:
                    diag["Stock on Market"] += 1
                    continue
                if dsr is None or dsr < min_dsr:
                    diag["Demand / Supply"] += 1
                    continue

                # ---------- ENGINE ----------
                factors = {
                    "renters_pct": renters,
                    "vacancy_pct": vacancy,
                    "demand_supply_ratio": dsr,
                    "stock_on_market_pct": stock,
                    "gross_rental_yield": gross_yield,
                    "statistical_reliability": reliability,
                }

                decision, failed = evaluate_buy_gates(factors)
                _, band = calculate_confidence(decision)

                rows.append({
                    "State": r.get("State"),
                    "Suburb": r.get("Suburb"),
                    "Decision": decision,
                    "Confidence": band,
                    "Failed Gates": ", ".join(failed) if failed else "None"
                })

            if not rows:
                st.warning("No suburbs matched your filters.")
                st.markdown("#### 🔍 Filter diagnostics (why rows were excluded)")
                diag_df = pd.DataFrame(
                    [{"Filter": k, "Rows Excluded": v} for k, v in diag.items() if v > 0]
                )
                st.dataframe(diag_df, use_container_width=True)
            else:
                st.subheader("📊 DSR Results (Filtered)")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ============================================================
# CLIENT 2 — EXPLORER (UNCHANGED)
# ============================================================
if client_mode == "I want to explore suburbs (No data)":
    st.info("Explorer path unchanged.")
