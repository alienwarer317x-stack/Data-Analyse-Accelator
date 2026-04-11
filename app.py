import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Cleaned & Fixed Logic Engine (v5 – Locked)")

# ====================== HELPER FUNCTIONS ======================
def normalise_percent(val):
    if pd.isna(val):
        return None
    try:
        val = float(str(val).replace("%", "").strip())
        return val * 100 if val <= 1 else val
    except:
        return None

def normalise_plain(val):
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None

# ====================== MAIN APP ======================
uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    results = []

    st.info("🔄 Running analysis with locked authoritative logic engine...")

    for _, row in df.iterrows():
        # -------- FACTOR MAPPING --------
        factors = {
            "renters_pct": normalise_percent(row.get("Percent renters in market")),
            "vacancy_pct": normalise_plain(row.get("Vacancy rate")),
            "demand_supply_ratio": normalise_plain(row.get("Demand to Supply Ratio")),
            "stock_on_market_pct": normalise_plain(row.get("Percent stock on market")),
            "gross_rental_yield": normalise_percent(row.get("Gross rental yield")),
            "statistical_reliability": normalise_plain(row.get("Statistical reliability")),
        }

        # -------- BUY GATES --------
        failed_gates = []
        if factors["renters_pct"] is None or not (15 <= factors["renters_pct"] <= 35):
            failed_gates.append("Renters %")
        if factors["vacancy_pct"] is None or factors["vacancy_pct"] >= 2:
            failed_gates.append("Vacancy")
        if factors["demand_supply_ratio"] is None or factors["demand_supply_ratio"] <= 55:
            failed_gates.append("Demand / Supply")
        if factors["stock_on_market_pct"] is None or factors["stock_on_market_pct"] >= 1.3:
            failed_gates.append("Stock on Market")
        if factors["gross_rental_yield"] is None or factors["gross_rental_yield"] <= 4:
            failed_gates.append("Gross Yield")
        if factors["statistical_reliability"] is None or factors["statistical_reliability"] <= 51:
            failed_gates.append("Reliability")

        decision = "BUY" if not failed_gates else "AVOID"
        confidence_score = 85 if decision == "BUY" else 60
        confidence_band = "High" if confidence_score >= 75 else "Medium"

        explanation = (
            "BUY: Meets all core eligibility gates."
            if decision == "BUY"
            else f"AVOID: Failed gates – {', '.join(failed_gates)}"
        )

        results.append({
            "Suburb": row.get("Suburb"),
            "Decision": decision,
            "Confidence": confidence_band,
            "Confidence Score": confidence_score,
            "RW-CAGR": None,
            "Renters %": factors["renters_pct"],
            "Vacancy %": factors["vacancy_pct"],
            "Demand / Supply": factors["demand_supply_ratio"],
            "Stock on Market %": factors["stock_on_market_pct"],
            "Gross Yield %": factors["gross_rental_yield"],
            "Failed Gates": ", ".join(failed_gates) if failed_gates else "None",
            "Explanation": explanation
        })

    # -------- DISPLAY --------
    summary_df = pd.DataFrame(results)
    summary_df = summary_df.sort_values(by=["Decision", "Confidence Score"], ascending=[False, False])

    st.subheader("📊 Investment Recommendation Summary")
    st.dataframe(summary_df, use_container_width=True, height=700)

    if not summary_df.empty:
        top = summary_df.iloc[0]
        st.success(f"🏆 **BEST SUBURB: {top['Suburb']}** — Decision: **{top['Decision']}**")

    # -------- DOWNLOAD --------
    output = BytesIO()
    summary_df.to_excel(output, index=False)
    st.download_button(
        "⬇️ Download Full Analysis",
        output.getvalue(),
        "Property_Investment_Accelerator_Results.xlsx"
    )

    st.info("✅ Logic engine locked. Results are now data-dependent, not code-dependent.")
