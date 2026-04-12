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
# INITIALISE SESSION STATE
# ============================================================
if "client_mode" not in st.session_state:
    st.session_state["client_mode"] = "I want to explore suburbs (No data)"

# ============================================================
# CLIENT TYPE SELECTION (SESSION‑CONTROLLED)
# ============================================================
st.markdown("### Choose how you want to use the Accelerator")

client_mode = st.radio(
    "Client Type",
    (
        "I have DSR data (Upload Spreadsheet)",
        "I want to explore suburbs (No data)"
    ),
    index=0 if st.session_state["client_mode"] == "I have DSR data (Upload Spreadsheet)" else 1,
    key="client_mode_radio"
)

# Keep session state in sync
st.session_state["client_mode"] = client_mode

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

def pick_price(row, mode):
    if mode == "House":
        return row.get("Median house price") or row.get("Median price")
    if mode == "Unit":
        return row.get("Median unit price") or row.get("Median price")
    return row.get("Median house price") or row.get("Median unit price") or row.get("Median price")

# ============================================================
# CLIENT TYPE 1 — DSR (AUTO‑SWITCH ENABLED)
# ============================================================
uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    # 🔥 AUTO‑SWITCH TO DSR MODE
    st.session_state["client_mode"] = "I have DSR data (Upload Spreadsheet)"
    st.experimental_rerun()

# Only run DSR UI if we are in DSR mode
if st.session_state["client_mode"] == "I have DSR data (Upload Spreadsheet)":

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("✅ DSR uploaded. Filters applied. Ready to run analysis.")

        if st.button("Run DSR Analysis"):

            rows = []
            diag = {
                "State": 0,
                "Property Type / Price": 0,
                "Days on Market": 0,
                "Renters Proportion": 0,
                "Vacancy": 0,
                "Gross Yield": 0,
                "Stock on Market": 0,
                "Demand / Supply": 0,
            }

            for _, r in df.iterrows():

                if selected_state != "All" and r.get("State") != selected_state:
                    diag["State"] += 1
                    continue

                price = pick_price(r, property_type)
                if price is not None and price > max_price:
                    diag["Property Type / Price"] += 1
                    continue

                dom = safe_int(r.get("Days on market"))
                renters = pct(r.get("Percent renters in market"))
                vacancy = pct(r.get("Vacancy rate"))
                stock = pct(r.get("Percent stock on market"))
                dsr = r.get("Demand to Supply Ratio")
                yield_ = pct(r.get("Gross rental yield"))
                reliability = r.get("Statistical reliability")

                if dom is None or dom > max_dom:
                    diag["Days on Market"] += 1
                    continue
                if renters is None or not (renters_min <= renters <= renters_max):
                    diag["Renters Proportion"] += 1
                    continue
                if vacancy is None or vacancy > max_vacancy:
                    diag["Vacancy"] += 1
                    continue
                if yield_ is None or yield_ < min_yield:
                    diag["Gross Yield"] += 1
                    continue
                if stock is None or stock > max_stock:
                    diag["Stock on Market"] += 1
                    continue
                if dsr is None or dsr < min_dsr:
                    diag["Demand / Supply"] += 1
                    continue

                decision, failed = evaluate_buy_gates({
                    "renters_pct": renters,
                    "vacancy_pct": vacancy,
                    "demand_supply_ratio": dsr,
                    "stock_on_market_pct": stock,
                    "gross_rental_yield": yield_,
                    "statistical_reliability": reliability,
                })

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
                st.markdown("#### 🔍 Filter diagnostics")
                st.dataframe(
                    pd.DataFrame(
                        [{"Filter": k, "Rows Excluded": v} for k, v in diag.items() if v > 0]
                    ),
                    use_container_width=True
                )
            else:
                st.subheader("📊 DSR Results (Filtered)")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ============================================================
# CLIENT TYPE 2 — EXPLORER
# ============================================================
if st.session_state["client_mode"] == "I want to explore suburbs (No data)":
    st.info("Explorer path active.")
