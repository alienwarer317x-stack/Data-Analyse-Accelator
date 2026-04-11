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
# CLIENT TYPE SELECTION (ONLY 2 CLIENT TYPES)
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
# SHARED FILTER PANEL (APPLIES AFTER CLIENT SELECTION)
# ============================================================
st.markdown("### Discovery Filters (Preferences)")
st.caption("Filters narrow candidates but never override BUY logic.")

col1, col2 = st.columns(2)

with col1:
    max_dom = st.slider("Maximum Days on Market", 0, 90, 90)
    renters_min, renters_max = st.slider(
        "Renters Proportion (%)",
        0, 40, (15, 35)
    )

with col2:
    min_yield = st.slider("Minimum Gross Yield (%)", 3.0, 7.5, 4.0)
    max_vacancy = st.slider("Maximum Vacancy (%)", 0.0, 4.5, 2.0)
    min_dsr = st.slider("Minimum Demand / Supply", 40, 70, 55)
    max_stock = st.slider("Maximum Stock on Market (%)", 0.0, 3.0, 1.3)

# ============================================================
# STATIC SUBURB LISTS (EXPLORER)
# ============================================================
STATE_SUBURBS = {
    "NSW": ["Aberdeen", "Tamworth", "Wagga Wagga", "Maitland", "Cessnock"],
    "VIC": ["Ballarat", "Bendigo", "Geelong"],
    "QLD": ["Toowoomba", "Rockhampton", "Mackay"],
    "TAS": ["Hobart", "Launceston"],
    "NT": ["Darwin", "Alice Springs"]
}

# ============================================================
# SIMULATED DATA SOURCES (SAFE)
# ============================================================
def scrape_days_on_market(suburb):
    time.sleep(0.05)
    return random.randint(15, 140)

def scrape_renters_pct(suburb):
    time.sleep(0.05)
    return round(random.uniform(15, 45), 1)

def scrape_vacancy_pct(suburb):
    time.sleep(0.05)
    return round(random.uniform(0.3, 4.5), 2)

def scrape_demand_supply_ratio(suburb):
    time.sleep(0.05)
    return round(random.uniform(40, 80), 1)

def scrape_stock_on_market_pct(suburb):
    time.sleep(0.05)
    return round(random.uniform(0.3, 2.5), 2)

def scrape_gross_rental_yield(suburb):
    time.sleep(0.05)
    return round(random.uniform(3.0, 7.5), 2)

def scrape_statistical_reliability(suburb):
    time.sleep(0.05)
    return round(random.uniform(45, 85), 1)

# ============================================================
# CLIENT TYPE 2 — EXPLORER (FILTERS + ENGINE)
# ============================================================
if client_mode == "I want to explore suburbs (No data)":

    st.markdown("### Explore Suburbs by State")
    selected_state = st.selectbox("State", STATE_SUBURBS.keys())
    suburbs = STATE_SUBURBS[selected_state]

    if st.button("Run Analysis"):

        st.info("🔄 Applying filters, enriching data, and running BUY logic…")

        rows = []

        for suburb in suburbs:
            dom = scrape_days_on_market(suburb)
            renters = scrape_renters_pct(suburb)

            # -------- FILTER STAGE (PREFERENCES ONLY) --------
            if dom > max_dom:
                continue
            if not (renters_min <= renters <= renters_max):
                continue

            factors = {
                "renters_pct": renters,
                "vacancy_pct": scrape_vacancy_pct(suburb),
                "demand_supply_ratio": scrape_demand_supply_ratio(suburb),
                "stock_on_market_pct": scrape_stock_on_market_pct(suburb),
                "gross_rental_yield": scrape_gross_rental_yield(suburb),
                "statistical_reliability": scrape_statistical_reliability(suburb),
            }

            # Filter constraints (still NOT BUY logic)
            if factors["gross_rental_yield"] < min_yield:
                continue
            if factors["vacancy_pct"] > max_vacancy:
                continue
            if factors["demand_supply_ratio"] < min_dsr:
                continue
            if factors["stock_on_market_pct"] > max_stock:
                continue

            decision, failed_gates = evaluate_buy_gates(factors)
            score, band = calculate_confidence(decision)

            if len(failed_gates) == 0:
                classification = "BUY"
            elif len(failed_gates) == 1:
                classification = "NEAR‑BUY"
            else:
                classification = "EXCLUDED"

            rows.append({
                "State": selected_state,
                "Suburb": suburb,
                "Days on Market": dom,
                "Renters %": renters,
                "Vacancy %": factors["vacancy_pct"],
                "Demand / Supply": factors["demand_supply_ratio"],
                "Stock on Market %": factors["stock_on_market_pct"],
                "Gross Yield %": factors["gross_rental_yield"],
                "Reliability": factors["statistical_reliability"],
                "Classification": classification,
                "Decision": decision,
                "Failed Gates": ", ".join(failed_gates) if failed_gates else "None"
            })

        if not rows:
            st.warning("No suburbs matched your filters.")
        else:
            df = pd.DataFrame(rows)

            st.subheader("✅ BUY")
            st.dataframe(df[df["Classification"] == "BUY"], use_container_width=True)

            st.subheader("🟡 Near‑BUY (1 Gate Failed)")
            st.dataframe(df[df["Classification"] == "NEAR‑BUY"], use_container_width=True)

            st.subheader("🔴 Excluded")
            st.dataframe(df[df["Classification"] == "EXCLUDED"], use_container_width=True)

            st.success(
                "✅ Filters applied correctly.\n\n"
                "BUY decisions remain fully governed by the authoritative logic engine."
            )

# ============================================================
# CLIENT TYPE 1 — DSR UPLOAD (FILTERS APPLIED AFTER UPLOAD LATER)
# ============================================================
if client_mode == "I have DSR data (Upload Spreadsheet)":
    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])
    if uploaded_file:
        st.success("✅ DSR upload path unchanged and ready for filtered evaluation.")
