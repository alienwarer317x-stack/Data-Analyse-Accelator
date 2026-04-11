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
# CLIENT TYPE SELECTION (ONLY 2)
# ============================================================
client_mode = st.radio(
    "Client Type",
    (
        "I have DSR data (Upload Spreadsheet)",
        "I want to explore suburbs (No data)"
    )
)

# ============================================================
# SHARED FILTERS (PREFERENCES LAYER)
# ============================================================
st.markdown("### Discovery Filters (Preferences)")
st.caption("Filters narrow candidates but never override BUY logic.")

col1, col2 = st.columns(2)

with col1:
    selected_state = st.selectbox(
        "State",
        ["All", "NSW", "VIC", "QLD", "TAS", "NT"]
    )
    property_type = st.radio(
        "Property Type",
        ["House", "Unit", "Both"],
        horizontal=True
    )
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
    renters_min, renters_max = st.slider(
        "Renters Proportion (%)",
        0, 40, (15, 35)
    )

with col2:
    max_price = st.slider(
        "Maximum Median Price ($)",
        200_000, 2_000_000, 1_000_000, step=50_000
    )
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
# CLIENT 1 — DSR UPLOAD (FILTERS + ENGINE)
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

                # ---------- STATE FILTER ----------
                if selected_state != "All":
                    if r.get("State") != selected_state:
                        continue

                # ---------- PROPERTY TYPE SELECTION ----------
                if property_type == "House":
                    median_price = r.get("Median house price")
                    gross_yield = pct(r.get("Gross house rental yield") or r.get("Gross rental yield"))
                elif property_type == "Unit":
                    median_price = r.get("Median unit price")
                    gross_yield = pct(r.get("Gross unit rental yield") or r.get("Gross rental yield"))
                else:
                    # Both → prefer house if available
                    median_price = r.get("Median house price") or r.get("Median unit price")
                    gross_yield = pct(r.get("Gross rental yield"))

                if median_price is None or median_price > max_price:
                    continue

                # ---------- OTHER NORMALISATION ----------
                dom = safe_int(r.get("Days on market"))
                renters = pct(r.get("Percent renters in market"))
                vacancy = pct(r.get("Vacancy rate"))
                stock = pct(r.get("Percent stock on market"))
                dsr = r.get("Demand to Supply Ratio")
                reliability = r.get("Statistical reliability")

                # ---------- FILTER STAGE ----------
                if dom is None or dom > max_dom:
                    continue
                if renters is None or not (renters_min <= renters <= renters_max):
                    continue
                if vacancy is None or vacancy > max_vacancy:
                    continue
                if gross_yield is None or gross_yield < min_yield:
                    continue
                if stock is None or stock > max_stock:
                    continue
                if dsr is None or dsr < min_dsr:
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
                    "Property Type": property_type,
                    "Median Price": median_price,
                    "Decision": decision,
                    "Confidence": band,
                    "Failed Gates": ", ".join(failed) if failed else "None"
                })

            if not rows:
                st.warning(
                    "No suburbs matched your filters.\n\n"
                    "Tip: widen Median Price, Vacancy, or Days on Market."
                )
            else:
                st.subheader("📊 DSR Results (Filtered)")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ============================================================
# CLIENT 2 — EXPLORER (STATE + PROPERTY TYPE + FILTERS)
# ============================================================
if client_mode == "I want to explore suburbs (No data)":

    STATE_SUBURBS = {
        "NSW": ["Aberdeen", "Tamworth", "Wagga Wagga", "Maitland", "Cessnock"],
        "VIC": ["Ballarat", "Bendigo", "Geelong"],
        "QLD": ["Toowoomba", "Rockhampton", "Mackay"],
        "TAS": ["Hobart", "Launceston"],
        "NT": ["Darwin", "Alice Springs"]
    }

    state = selected_state if selected_state != "All" else st.selectbox(
        "State", STATE_SUBURBS.keys()
    )

    suburbs = STATE_SUBURBS[state]

    if st.button("Run Explorer Analysis"):

        rows = []

        for suburb in suburbs:
            # Simulated values
            dom = random.randint(15, 140)
            renters = random.uniform(15, 45)
            vacancy = random.uniform(0.3, 4.5)
            dsr = random.uniform(40, 80)
            stock = random.uniform(0.3, 2.5)
            yield_ = random.uniform(3.0, 8.0)
            reliability = random.uniform(45, 85)
            price = random.randint(250_000, 1_800_000)

            # ---------- FILTER STAGE ----------
            if dom > max_dom:
                continue
            if not (renters_min <= renters <= renters_max):
                continue
            if vacancy > max_vacancy:
                continue
            if yield_ < min_yield:
                continue
            if stock > max_stock:
                continue
            if dsr < min_dsr:
                continue
            if price > max_price:
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

            category = (
                "BUY" if not failed else
                "NEAR‑BUY" if len(failed) == 1 else
                "EXCLUDED"
            )

            rows.append({
                "State": state,
                "Suburb": suburb,
                "Property Type": property_type,
                "Median Price": price,
                "Days on Market": dom,
                "Decision": decision,
                "Category": category,
                "Failed Gates": ", ".join(failed) if failed else "None"
            })

        if not rows:
            st.warning("No suburbs matched your filters.")
        else:
            df = pd.DataFrame(rows)

            st.subheader("✅ BUY")
            st.dataframe(df[df["Category"] == "BUY"], use_container_width=True)

            st.subheader("🟡 Near‑BUY")
            st.dataframe(df[df["Category"] == "NEAR‑BUY"], use_container_width=True)

            st.subheader("🔴 Excluded")
            st.dataframe(df[df["Category"] == "EXCLUDED"], use_container_width=True)
