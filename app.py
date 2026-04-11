import streamlit as st
import pandas as pd
from io import BytesIO

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
# CLIENT TYPE SELECTION (STEP 1)
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
# HELPER FUNCTIONS
# ============================================================

def normalise_percent(val):
    """
    Handles:
    0.24  -> 24
    24    -> 24
    '24%' -> 24
    """
    if pd.isna(val):
        return None
    try:
        val = float(str(val).replace("%", "").strip())
        return val * 100 if val <= 1 else val
    except:
        return None

def normalise_plain(val):
    """
    Handles values already in % or index form:
    Vacancy %, Stock %, Demand/Supply
    """
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None

# ============================================================
# CLIENT TYPE 2 — STATE SELECTION (NO SCRAPING YET)
# ============================================================
