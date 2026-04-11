import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Fixed Mapping + Realistic Scoring (v2)")

uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    results = []

    st.info("🔄 Running analysis with improved DSR mapping...")

    for _, row in df.iterrows():
        # ==================== IMPROVED DSR MAPPING ====================
        factors = {
            "renters_pct": pd.to_numeric(row.get("Percent renters in market"), errors='coerce'),
            "vacancy_pct": pd.to_numeric(row.get("Vacancy rate"), errors='coerce'),
            "demand_supply_ratio": pd.to_numeric(row.get("Demand to Supply Ratio"), errors='coerce'),
            "stock_on_market_pct": pd.to_numeric(row.get("Percent stock on market"), errors='coerce'),
            "days_on_market": pd.to_numeric(str(row.get("Days on market", "")).replace("days", ""), errors='coerce'),
            "auction_clearance_pct": pd.to_numeric(row.get("Auction clearance rate"), errors='coerce'),
            "vendor_discount_pct": pd.to_numeric(row.get("Avg vendor discount"), errors='coerce'),
            "online_search_index": pd.to_numeric(row.get("Online search interest"), errors='coerce'),
            "median_12m_change": pd.to_numeric(row.get("Median 12 months"), errors='coerce'),
            "statistical_reliability": pd.to_numeric(row.get("Statistical reliability"), errors='coerce'),
            "gross_rental_yield": pd.to_numeric(row.get("Gross rental yield"), errors='coerce'),
            "typical_value": pd.to_numeric(row.get("Typical value"), errors='coerce'),
        }

        # ==================== BUY GATES (tolerant version) ====================
        gates_passed = True
        failed_gates = []

        if factors["renters_pct"] is None or not (15 <= factors["renters_pct"] <= 35):
            gates_passed = False
            failed_gates.append("Renters %")
        if factors["vacancy_pct"] is None or factors["vacancy_pct"] >= 2:
            gates_passed = False
            failed_gates.append("Vacancy")
        if factors["demand_supply_ratio"] is None or factors["demand_supply_ratio"] <= 55:
            gates_passed = False
            failed_gates.append("DSR")
        if factors["stock_on_market_pct"] is None or factors["stock_on_market_pct"] >= 1.3:
            gates_passed = False
            failed_gates.append("Stock on market")
        if factors["gross_rental_yield"] is None or factors["gross_rental_yield"] <= 0.04:   # 4% = 0.04
            gates_passed = False
            failed_gates.append("Gross Yield")
        if factors["statistical_reliability"] is None or factors["statistical_reliability"] <= 51:
            gates_passed = False
            failed_gates.append("Reliability")

        decision = "BUY" if gates_passed else "AVOID"
        confidence_score = 85 if decision == "BUY" else 60
        confidence_band = "High" if confidence_score >= 75 else "Medium"

        explanation = f"{decision}: "
        if decision == "BUY":
            explanation += "Meets all core eligibility gates."
        else:
            explanation += f"Failed gates: {', '.join(failed_gates)}"

        results.append({
            "Suburb": row["Suburb"],
            "Decision": decision,
            "Confidence": confidence_band,
            "Confidence Score": confidence_score,
            "RW-CAGR": None,
            "Explanation": explanation,
            "Demand to Supply Ratio": factors["demand_supply_ratio"],
            "Vacancy %": factors["vacancy_pct"],
            "Gross Yield %": factors["gross_rental_yield"],
            "Failed Gates": ", ".join(failed_gates) if failed_gates else "None"
        })

    # ====================== DISPLAY ======================
    summary_df = pd.DataFrame(results)
    summary_df = summary_df.sort_values(by="Confidence Score", ascending=False)

    st.subheader("📊 Investment Recommendation Summary")
    st.dataframe(summary_df, use_container_width=True, height=700)

    if not summary_df.empty:
        top = summary_df.iloc[0]
        st.success(f"🏆 **BEST SUBURB: {top['Suburb']}** — Decision: **{top['Decision']}**")

    output = BytesIO()
    summary_df.to_excel(output, index=False)
    st.download_button("⬇️ Download Full Analysis", output.getvalue(), "Accelerator_Results.xlsx")
