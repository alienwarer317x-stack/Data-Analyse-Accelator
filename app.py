import streamlit as st
import pandas as pd
from engine import evaluate_buy_gates, calculate_confidence

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two‑Stage Discovery + Authoritative Logic Engine")

# ====================== SESSION STATE ======================
if "discovery_df" not in st.session_state:
    st.session_state.discovery_df = None

if "selected_suburbs" not in st.session_state:
    st.session_state.selected_suburbs = set()

# ====================== CLIENT MODE ======================
client_mode = st.radio(
    "Client Type",
    ("DSR Upload", "Explorer"),
    horizontal=True
)

# ====================== STAGE 1 — DISCOVERY FILTERS ======================
st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences Only)")
st.caption("Neutral discovery only. No investment logic or BUY rules applied.")

col1, col2 = st.columns(2)

with col1:
    selected_state = st.selectbox(
        "State",
        ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"]
    )
    max_dom = st.slider(
        "Maximum Days on Market",
        0, 180, 90
    )

with col2:
    max_price = st.slider(
        "Maximum Median Price ($)",
        200_000, 2_000_000, 1_000_000,
        step=50_000
    )

# ====================== APPLY + RESET BUTTONS ======================
btn_apply, btn_reset = st.columns([1, 1])

apply_clicked = btn_apply.button("Apply Discovery Filters")
reset_clicked = btn_reset.button("Reset")

if reset_clicked:
    st.session_state.discovery_df = None
    st.session_state.selected_suburbs = set()

# ====================== HELPERS ======================
def normalise_plain(val):
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None

def normalise_percent(val):
    try:
        v = float(str(val).replace("%", "").strip())
        return v * 100 if v <= 1 else v
    except:
        return None

def fmt_currency(val):
    return f"${val:,.0f}" if val is not None else ""

# ====================== STAGE 1 — DISCOVERY (DSR UPLOAD) ======================
if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded_file and apply_clicked:
        df = pd.read_excel(uploaded_file)

        discovered = []

        for _, r in df.iterrows():
            if selected_state != "All" and r.get("State") != selected_state:
                continue

            dom = normalise_plain(r.get("Days on market"))
            price = (
                normalise_plain(r.get("Typical value"))
                or normalise_plain(r.get("Median 12 months"))
            )
            yld = normalise_percent(r.get("Gross rental yield"))

            # ✅ STAGE 1 — STRUCTURAL FILTERS ONLY
            if dom is None or dom > max_dom:
                continue
            if price is not None and price > max_price:
                continue

            discovered.append({
                "State": r.get("State"),
                "Suburb": r.get("Suburb"),
                "Median Price ($)": fmt_currency(price),
                "Rental Yield (%)": round(yld, 2) if yld is not None else None,
                "Days on Market": int(dom),
                "_row": r
            })

        if discovered:
            st.session_state.discovery_df = pd.DataFrame(discovered)
            st.session_state.selected_suburbs = set(
                st.session_state.discovery_df["Suburb"]
            )
        else:
            st.session_state.discovery_df = None
            st.session_state.selected_suburbs = set()
            st.warning(
                "⚠️ No suburbs matched your discovery filters.\n\n"
                "Try widening price or days on market."
            )

# ====================== STAGE 1 RESULTS — SINGLE TABLE ======================
if st.session_state.discovery_df is not None and not st.session_state.discovery_df.empty:
    st.markdown("## 📍 Discovery Results")

    st.dataframe(
        st.session_state.discovery_df[
            ["State", "Suburb", "Median Price ($)", "Rental Yield (%)", "Days on Market"]
        ],
        use_container_width=True
    )

    # Client selection only (no logic)
    all_suburbs = st.session_state.discovery_df["Suburb"].tolist()
    selected = st.multiselect(
        "Select suburbs for Deep Analysis",
        options=all_suburbs,
        default=all_suburbs
    )
    st.session_state.selected_suburbs = set(selected)

# ====================== STAGE 2 — DEEP ANALYSIS (ENGINE ONLY) ======================
if st.session_state.selected_suburbs:
    st.markdown("## 🟥 Stage 2 — Deep Analysis (Authoritative Engine)")

    if st.button("Run Deep Analysis on Selected Suburbs"):
        results = []

        for _, r in st.session_state.discovery_df.iterrows():
            if r["Suburb"] not in st.session_state.selected_suburbs:
                continue

            row = r["_row"]

            # ✅ ENGINE LOGIC — STAGE 2 ONLY
            factors = {
                "renters_pct": normalise_percent(row.get("Percent renters in market")),
                "vacancy_pct": normalise_plain(row.get("Vacancy rate")),
                "demand_supply_ratio": normalise_plain(row.get("Demand to Supply Ratio")),
                "stock_on_market_pct": normalise_plain(row.get("Percent stock on market")),
                "gross_rental_yield": normalise_percent(row.get("Gross rental yield")),
                "statistical_reliability": normalise_plain(row.get("Statistical reliability")),
            }

            decision, failed = evaluate_buy_gates(factors)
            score, band = calculate_confidence(decision)

            results.append({
                "Suburb": r["Suburb"],
                "Decision": decision,
                "Confidence": band,
                "Confidence Score": score,
                "Failed Gates": ", ".join(failed) if failed else "None"
            })

        st.subheader("✅ Deep Analysis Results")
        st.dataframe(pd.DataFrame(results), use_container_width=True)

st.caption("Property Investment Accelerator — Authoritative Logic Engine")
