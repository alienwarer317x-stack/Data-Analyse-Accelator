import streamlit as st
import pandas as pd
import random
import time

from engine import (
    evaluate_buy_gates,
    calculate_confidence
)

# ============================================================
# APP SETUP
# ============================================================
st.set_page_config(
    page_title="Property Investment Accelerator",
    layout="wide"
)

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
# SHARED FILTER PANEL (PREFERENCES)
# ============================================================
st.markdown("### Discovery Filters (Preferences)")
st.caption("Filters narrow candidates but never override BUY logic.")

col1, col2 = st.columns(2)

with col1:
    max_dom = st.slider("Maximum Days on Market", 0, 90, 90)
    renters_min, renters_max = st.slider("Renters Proportion (%)", 0, 40, (15, 35))

with col2:
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 7.5, 4.0)
    max_vacancy = st.slider("Maximum Vacancy (%)", 0.0, 4.5, 2.0)
    min_dsr = st.slider("Minimum Demand / Supply", 40, 70, 55)
    max_stock = st.slider("Maximum Stock on Market (%)", 0.0, 3.0, 1.3)

# ============================================================
# CLIENT TYPE 1 — DSR UPLOAD (NOW FULLY WIRED)
# ============================================================
if client_mode == "I have DSR data (Upload Spreadsheet)":

    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("✅ DSR uploaded. Apply filters and run analysis.")

        if st.button("Run DSR Analysis"):

            st.info("🔄 Applying filters and running BUY logic on DSR data…")

            rows = []

            for _, row in df.iterrows():

                # ---- FILTER STAGE ----
                if row.get("Days on Market", 0) > max_dom:
                    continue

                renters = row.get("Percent renters in market", None)
                if renters is not None and not (renters_min <= renters <= renters_max):
                    continue

                if row.get("Gross rental yield", 0) < min_yield:
                    continue

                if row.get("Vacancy rate", 0) > max_vacancy:
                    continue

                if row.get("Demand to Supply Ratio", 0) < min_dsr:
                    continue

                if row.get("Percent stock on market", 0) > max_stock:
                    continue

                # ---- ENGINE FACTORS ----
                factors = {
                    "renters_pct": renters,
                    "vacancy_pct": row.get("Vacancy rate"),
                    "demand_supply_ratio": row.get("Demand to Supply Ratio"),
                    "stock_on_market_pct": row.get("Percent stock on market"),
                    "gross_rental_yield": row.get("Gross rental yield"),
                    "statistical_reliability": row.get("Statistical reliability"),
                }

                decision, failed_gates = evaluate_buy_gates(factors)
                score, band = calculate_confidence(decision)

                rows.append({
                    "Suburb": row.get("Suburb"),
                    "Decision": decision,
                    "Confidence": band,
                    "Failed Gates": ", ".join(failed_gates) if failed_gates else "None"
                })

            if not rows:
                st.warning("No DSR rows matched your filters.")
            else:
                st.subheader("📊 DSR Results (Filtered)")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

                st.success(
                    "✅ DSR analysis complete.\n\n"
                    "Filters applied first. BUY logic enforced by engine."
                )

# ============================================================
# CLIENT TYPE 2 — EXPLORER (UNCHANGED)
# ============================================================
if client_mode == "I want to explore suburbs (No data)":

    STATE_SUBURBS = {
        "NSW": ["Aberdeen", "Tamworth", "Wagga Wagga", "Maitland", "Cessnock"],
        "VIC": ["Ballarat", "Bendigo", "Geelong"],
        "QLD": ["Toowoomba", "Rockhampton", "Mackay"],
    }

    selected_state = st.selectbox("State", STATE_SUBURBS.keys())

    def r(a, b): return round(random.uniform(a, b), 2)

    if st.button("Run Analysis"):

        rows = []

        for suburb in STATE_SUBURBS[selected_state]:

            factors = {
                "renters_pct": r(15, 40),
                "vacancy_pct": r(0.3, 4.5),
                "demand_supply_ratio": r(40, 80),
                "stock_on_market_pct": r(0.3, 2.5),
                "gross_rental_yield": r(3.0, 7.5),
                "statistical_reliability": r(45, 85),
            }

            decision, failed_gates = evaluate_buy_gates(factors)
            score, band = calculate_confidence(decision)

            rows.append({
                "Suburb": suburb,
                "Decision": decision,
                "Failed Gates": ", ".join(failed_gates)
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True)
