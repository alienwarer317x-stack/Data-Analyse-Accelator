import streamlit as st
import pandas as pd
from io import BytesIO
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Fixed Mapping + Full Logic Engine")

# ====================== MASTER FACTORS & GATES ======================
BUY_GATES = {
    "renters_pct": (15, 35),
    "vacancy_pct": "<2",
    "demand_supply_ratio": ">55",
    "stock_on_market_pct": "<1.3",
    "gross_rental_yield": ">4",
    "statistical_reliability": ">51"
}

def safe_num(v):
    if v is None or pd.isna(v):
        return None
    try:
        return float(str(v).replace('%', '').replace('days', ''))
    except:
        return None

# ====================== MAIN APP ======================
uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    results = []

    st.info("🔄 Running full analysis with corrected DSR mapping...")

    for _, row in df.iterrows():
        # ==================== FIXED DSR MAPPING ====================
        factors = {
            "renters_pct": safe_num(row.get("Percent renters in market")),
            "vacancy_pct": safe_num(row.get("Vacancy rate")),
            "demand_supply_ratio": safe_num(row.get("Demand to Supply Ratio")),
            "stock_on_market_pct": safe_num(row.get("Percent stock on market")),
            "days_on_market": safe_num(row.get("Days on market")),
            "auction_clearance_pct": safe_num(row.get("Auction clearance rate")),
            "vendor_discount_pct": safe_num(row.get("Avg vendor discount")),
            "online_search_index": safe_num(row.get("Online search interest")),
            "median_12m_change": safe_num(row.get("Median 12 months")),
            "statistical_reliability": safe_num(row.get("Statistical reliability")),
            "gross_rental_yield": safe_num(row.get("Gross rental yield")),
            "typical_value": safe_num(row.get("Typical value")),
            # Future scraped fields (still pending)
            "sqm_cagr_10y": None,
            "oth_10y_growth": None,
            "htag_cagr_10y": None,
            "building_approvals_18m": None,
            "employment_diversity": None,
        }

        # ==================== LOGIC ENGINE ====================
        rw_cagr = None  # Will be filled when growth scrapers are added
        decision = "AVOID"
        if all([
            factors["renters_pct"] is not None and 15 <= factors["renters_pct"] <= 35,
            factors["vacancy_pct"] is not None and factors["vacancy_pct"] < 2,
            factors["demand_supply_ratio"] is not None and factors["demand_supply_ratio"] > 55,
            factors["stock_on_market_pct"] is not None and factors["stock_on_market_pct"] < 1.3,
            factors["gross_rental_yield"] is not None and factors["gross_rental_yield"] > 4,
            factors["statistical_reliability"] is not None and factors["statistical_reliability"] > 51,
        ]):
            decision = "BUY"

        confidence_score = 85 if decision == "BUY" else 60
        confidence_band = "High" if confidence_score >= 75 else "Medium"

        explanation = f"{decision}: "
        if decision == "BUY":
            explanation += "Meets all core eligibility gates."
        else:
            explanation += "Failed one or more core eligibility gates."

        results.append({
            "Suburb": row["Suburb"],
            "Decision": decision,
            "Confidence": confidence_band,
            "Confidence Score": confidence_score,
            "RW-CAGR": rw_cagr,
            "Explanation": explanation,
            "Demand to Supply Ratio": factors["demand_supply_ratio"],
            "Vacancy %": factors["vacancy_pct"],
            "Gross Yield %": factors["gross_rental_yield"]
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
    st.download_button("⬇️ Download Full Analysis", output.getvalue(), "Property_Investment_Accelerator_Results.xlsx")

    st.info("✅ Mapping fixed. More scrapers (SQM, HTAG, OnTheHouse, AreaSearch) will be added next.")
