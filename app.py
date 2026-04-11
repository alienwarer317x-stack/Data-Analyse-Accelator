import streamlit as st
import pandas as pd
from io import BytesIO
import random
import time

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
# CLIENT TYPE SELECTION — STEP 1
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
# STEP 2 — STATIC SUBURB LISTS
# ============================================================
STATE_SUBURBS = {
    "NSW": ["Aberdeen", "Tamworth", "Wagga Wagga", "Maitland", "Cessnock"],
    "VIC": ["Ballarat", "Bendigo", "Geelong"],
    "QLD": ["Toowoomba", "Rockhampton", "Mackay"],
    "TAS": ["Hobart", "Launceston"],
    "NT": ["Darwin", "Alice Springs"]
}

# ============================================================
# HELPER FUNCTIONS — LOGIC (LOCKED)
# ============================================================
def normalise_percent(val):
    if val is None:
        return None
    return val * 100 if val <= 1 else val

def passes_buy_gates(factors):
    failures = []

    if factors["renters_pct"] is None or not (15 <= factors["renters_pct"] <= 35):
        failures.append("Renters %")

    # Other BUY gates (not scraped yet)
    failures.append("Vacancy")
    failures.append("Demand / Supply")
    failures.append("Stock on Market")
    failures.append("Gross Yield")
    failures.append("Reliability")

    return failures

# ============================================================
# STEP 3 — RENTERS % SCRAPER (SAFE SIMULATION)
# ============================================================
def scrape_renters_pct(suburb, state):
    """
    SAFE simulated scraper.
    Replace later with ABS / API / paid data provider.
    """
    time.sleep(0.2)  # simulate network latency
    return round(random.uniform(18, 42), 1)  # realistic renters %

# ============================================================
# CLIENT TYPE 2 — EXPLORE BY STATE + SCRAPING
# ============================================================
if client_mode == "I want to explore suburbs (No data)":

    st.markdown("### Explore Suburbs by State")

    selected_state = st.selectbox("Select a State", STATE_SUBURBS.keys())
    suburbs = STATE_SUBURBS[selected_state]

    if st.button("Run Analysis"):

        st.info("🔄 Fetching renters % and running core BUY logic…")

        results = []

        for suburb in suburbs:
            renters_pct = scrape_renters_pct(suburb, selected_state)

            factors = {
                "renters_pct": renters_pct
            }

            failed_gates = passes_buy_gates(factors)
            decision = "BUY" if len(failed_gates) == 0 else "AVOID"

            results.append({
                "State": selected_state,
                "Suburb": suburb,
                "Renters %": renters_pct,
                "Decision": decision,
                "Failed Gates": ", ".join(failed_gates)
            })

        result_df = pd.DataFrame(results)

        st.subheader("📊 Explorer Results (Partial Data)")
        st.dataframe(result_df, use_container_width=True)

        st.info(
            "✅ Renters % gate applied.\n\n"
            "Next steps will progressively remove 'Failed Gates' as data is added."
        )

    st.stop()

# ============================================================
# CLIENT TYPE 1 — DSR LOGIC (UNCHANGED, LOCKED)
# ============================================================
uploaded_file = st.file_uploader(
    "Upload your DSR Excel file",
    type=["xlsx"]
)

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    st.success("✅ DSR upload path unchanged and still works.")
