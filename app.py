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
# STEP 2 — STATIC SUBURB LISTS (NO SCRAPING)
# ============================================================

STATE_SUBURBS = {
    "NSW": [
        "Aberdeen", "Tamworth", "Wagga Wagga", "Maitland",
        "Cessnock", "Albury", "Armidale", "Dubbo"
    ],
    "VIC": [
        "Ballarat", "Bendigo", "Geelong", "Shepparton",
        "Mildura", "Traralgon"
    ],
    "QLD": [
