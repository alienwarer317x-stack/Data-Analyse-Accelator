import streamlit as st
import pandas as pd
import random

from engine import evaluate_buy_gates, calculate_confidence

# ============================================================
# APP SETUP
# ============================================================
st.set_page_config(page_title="Property Investment Accelerator", layout="wide")

st.title("🏠 Property Investment Accelerator")
st.subheader("Authoritative Logic Engine · Multi‑Client Platform")

# ============================================================
# SESSION STATE INITIALISATION
# ============================================================
if "client_mode" not in st.session_state:
    st.session_state.client_mode = "I want to explore suburbs (No data)"

# ============================================================
# CLIENT TYPE SELECTION
# ============================================================
st.markdown("### Choose how you want to use the Accelerator")

client_mode = st.radio(
    "Client Type",
    (
        "I have DSR data (Upload Spreadsheet)",
        "I want to explore suburbs (No data)"
    ),
    index=0 if st.session_state.client_mode == "I have DSR data (Upload Spreadsheet)" else 1,
)

st.session_state.client_mode = client_mode

# ============================================================
# SHARED FILTER PANEL (PREFERENCES)
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
# HELPER FUNCTIONS
# ============================================================
def pct(val):
    try:
        v = float(val)
        return v * 100 if v <= 1 else v
    except:
        return None

def safe_int(val):
    try:
        return int(float(val))
    except:
        return None

# ============================================================
# CLIENT TYPE 1 — DSR MODE
# ============================================================
if st.session_state.client_mode == "I have DSR data (Upload Spreadsheet)":

    uploaded_file = st.file_uploader(
        "Upload your DSR Excel file",
        type=["xlsx"],
        key="dsr_uploader"
    )

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("✅ DSR uploaded. Adjust filters and run analysis.")

        if st.button("Run DSR Analysis"):

            results = []

            for _, r in df.iterrows():

                if selected_state != "All" and r.get("State") != selected_state:
                    continue

                dom = safe_int(r.get("Days on market"))
                renters = pct(r.get("Percent renters in market"))
                vacancy = pct(r.get("Vacancy rate"))
                yield_ = pct(r.get("Gross rental yield"))
                stock = pct(r.get("Percent stock on market"))
                dsr = r.get("Demand to Supply Ratio")
                reliability = r.get("Statistical reliability")

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

                decision, failed = evaluate_buy_gates({
                    "renters_pct": renters,
                    "vacancy_pct": vacancy,
                    "demand_supply_ratio": dsr,
                    "stock_on_market_pct": stock,
                    "gross_rental_yield": yield_,
                    "statistical_reliability": reliability,
                })

                _, band = calculate_confidence(decision)

                results.append({
                    "State": r.get("State"),
                    "Suburb": r.get("Suburb"),
                    "Decision": decision,
                    "Confidence": band,
                    "Failed Gates": ", ".join(failed) if failed else "None",
                })

            if results:
                st.subheader("📊 DSR Results")
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.warning("No suburbs matched your filters.")

# ============================================================
# CLIENT TYPE 2 — EXPLORER MODE (ANALYSE ADDED ✅)
# ============================================================
if st.session_state.client_mode == "I want to explore suburbs (No data)":

    STATE_SUBURBS = {
        "NSW": ["Aberdeen", "Tamworth", "Wagga Wagga", "Maitland", "Cessnock"],
        "VIC": ["Ballarat", "Bendigo", "Geelong"],
        "QLD": ["Toowoomba", "Rockhampton", "Mackay"],
        "TAS": ["Hobart", "Launceston"],
        "NT": ["Darwin", "Alice Springs"]
    }

    state = selected_state if selected_state != "All" else st.selectbox("State", STATE_SUBURBS.keys())

    suburbs = STATE_SUBURBS[state]

    if st.button("Run Explorer Analysis"):

        results = []

        for suburb in suburbs:
            # --- Simulated Explorer Data ---
            dom = random.randint(15, 160)
            renters = random.uniform(10, 45)
            vacancy = random.uniform(0.3, 4.5)
            dsr = random.uniform(40, 80)
            stock = random.uniform(0.3, 2.5)
            yield_ = random.uniform(3.0, 8.0)
            reliability = random.uniform(45, 85)
            price = random.randint(250_000, 1_800_000)

            # --- Filter stage ---
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

            decision, failed = evaluate_buy_gates({
                "renters_pct": renters,
                "vacancy_pct": vacancy,
                "demand_supply_ratio": dsr,
                "stock_on_market_pct": stock,
                "gross_rental_yield": yield_,
                "statistical_reliability": reliability,
            })

            _, band = calculate_confidence(decision)

            category = (
                "BUY" if not failed else
                "NEAR‑BUY" if len(failed) == 1 else
                "EXCLUDED"
            )

            results.append({
                "State": state,
                "Suburb": suburb,
                "Median Price": price,
                "Days on Market": dom,
                "Decision": decision,
                "Category": category,
                "Failed Gates": ", ".join(failed) if failed else "None",
            })

        if results:
            df = pd.DataFrame(results)

            st.subheader("✅ BUY")
            st.dataframe(df[df["Category"] == "BUY"], use_container_width=True)

            st.subheader("🟡 Near‑BUY")
            st.dataframe(df[df["Category"] == "NEAR‑BUY"], use_container_width=True)

            st.subheader("🔴 Excluded")
            st.dataframe(df[df["Category"] == "EXCLUDED"], use_container_width=True)
        else:
            st.warning("No suburbs matched your filters.")
