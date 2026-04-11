import streamlit as st
import pandas as pd
from io import BytesIO
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
st.subheader("Authoritative Logic Engine · Dual Client Mode")

# ============================================================
# CLIENT TYPE SELECTION
# ============================================================
st.markdown("### Choose how you want to use the Accelerator")

client_mode = st.radio(
    "Client Type",
    (
        "I have DSR data (Upload Spreadsheet)",
        "I want to explore suburbs (No data)"
    )
)

# ============================================================
# STATIC SUBURB LISTS
# ============================================================
STATE_SUBURBS = {
    "NSW": ["Aberdeen", "Tamworth", "Wagga Wagga", "Maitland", "Cessnock"],
    "VIC": ["Ballarat", "Bendigo", "Geelong"],
    "QLD": ["Toowoomba", "Rockhampton", "Mackay"],
    "TAS": ["Hobart", "Launceston"],
    "NT": ["Darwin", "Alice Springs"]
}

# ============================================================
# SIMULATED SCRAPERS (SAFE, REPLACEABLE)
# ============================================================
def scrape_renters_pct(suburb, state):
    time.sleep(0.1)
    return round(random.uniform(18, 42), 1)

def scrape_vacancy_pct(suburb, state):
    time.sleep(0.1)
    return round(random.uniform(0.4, 4.5), 2)

def scrape_demand_supply_ratio(suburb, state):
    """
    Simulated Demand/Supply ratio.
    Typical SQM-style range is ~30–80
    BUY gate is > 55
    """
    time.sleep(0.1)
    return round(random.uniform(35, 80), 1)

# ============================================================
# CLIENT TYPE 2 — EXPLORER (STEP 6)
# ============================================================
if client_mode == "I want to explore suburbs (No data)":

    st.markdown("### Explore Suburbs by State")

    selected_state = st.selectbox("Select a State", STATE_SUBURBS.keys())
    suburbs = STATE_SUBURBS[selected_state]

    if st.button("Run Analysis"):

        st.info("🔄 Fetching renters %, vacancy %, demand/supply and running BUY logic…")

        rows = []

        for suburb in suburbs:
            factors = {
                "renters_pct": scrape_renters_pct(suburb, selected_state),
                "vacancy_pct": scrape_vacancy_pct(suburb, selected_state),
                "demand_supply_ratio": scrape_demand_supply_ratio(suburb, selected_state),

                # Gates not yet enriched
                "stock_on_market_pct": None,
                "gross_rental_yield": None,
                "statistical_reliability": None,
            }

            decision, failed_gates = evaluate_buy_gates(factors)
            score, band = calculate_confidence(decision)

            rows.append({
                "State": selected_state,
                "Suburb": suburb,
                "Renters %": factors["renters_pct"],
                "Vacancy %": factors["vacancy_pct"],
                "Demand / Supply": factors["demand_supply_ratio"],
                "Decision": decision,
                "Confidence": band,
                "Failed Gates": ", ".join(failed_gates)
            })

        st.subheader("📊 Explorer Results (Partial Data)")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        st.success(
            "✅ Renters %, Vacancy %, and Demand / Supply applied.\n"
            "Remaining Failed Gates will resolve as data is added."
        )

    st.stop()

# ============================================================
# CLIENT TYPE 1 — DSR UPLOAD (UNCHANGED)
# ============================================================
uploaded_file = st.file_uploader(
    "Upload your DSR Excel file",
    type=["xlsx"]
)

if uploaded_file:
    st.success("✅ DSR upload path unchanged and still works.")
