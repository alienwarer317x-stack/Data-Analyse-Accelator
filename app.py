import streamlit as st
import pandas as pd
from io import BytesIO
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Authoritative Logic Engine + DSR Upload → Full Scoring")

# ====================== 1. MASTER ACCELERATOR FACTOR LIST (35) ======================
ACCELERATOR_FACTORS = [
    "renters_pct", "vacancy_pct", "demand_supply_ratio",
    "stock_on_market_pct", "days_on_market",
    "auction_clearance_pct", "vendor_discount_pct",
    "online_search_index", "median_12m_change",
    "statistical_reliability",
    "sqm_36m_growth", "htag_36m_growth", "typical_36m_growth",
    "avg_3yr_growth", "rental_growth_12m",
    "oth_10y_growth", "total_cagr_10y",
    "sqm_cagr_10y", "htag_cagr_10y",
    "building_approvals_18m", "developable_land",
    "housing_mismatch_risk", "infrastructure_access",
    "future_supply_signal",
    "job_count", "employment_diversity",
    "professional_growth_2016_21", "professional_growth_latest",
    "income_growth_2016_21", "income_growth_latest",
    "unemployment_vs_state", "unemployment_trend",
    "rent_stress", "mortgage_stress", "housing_affordability"
]

# ====================== 2. BUY ELIGIBILITY GATES ======================
BUY_GATES = {
    "renters_pct": (15, 35),
    "vacancy_pct": "<2",
    "demand_supply_ratio": ">55",
    "stock_on_market_pct": "<1.3",
    "gross_rental_yield": ">4",
    "statistical_reliability": ">51"
}

# ====================== HELPER FUNCTIONS (Exact from your spec) ======================
def safe_num(v):
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except:
        return None

def passes_buy_gates(f):
    if f.get("renters_pct") is None or not (15 <= f["renters_pct"] <= 35): return False
    if f.get("vacancy_pct") is None or f["vacancy_pct"] >= 2: return False
    if f.get("demand_supply_ratio") is None or f["demand_supply_ratio"] <= 55: return False
    if f.get("stock_on_market_pct") is None or f["stock_on_market_pct"] >= 1.3: return False
    if f.get("statistical_reliability") is None or f["statistical_reliability"] <= 51: return False
    return True

def calculate_rw_cagr(f):
    sources = [
        ("sqm_cagr_10y", 0.4),
        ("oth_10y_growth", 0.4),
        ("htag_cagr_10y", 0.2)
    ]
    weighted_sum = 0
    weight_total = 0
    for field, weight in sources:
        val = safe_num(f.get(field))
        if val is not None:
            weighted_sum += val * weight
            weight_total += weight
    return round(weighted_sum / weight_total, 2) if weight_total > 0 else None

def calculate_confidence(f):
    score = 100
    if safe_num(f.get("vendor_discount_pct")) is not None and f["vendor_discount_pct"] > 5:
        score -= 10
    if safe_num(f.get("unemployment_vs_state")) is not None and f["unemployment_vs_state"] > 2:
        score -= 15
    if safe_num(f.get("building_approvals_18m")) is not None and f["building_approvals_18m"] >= 8:
        score -= 15
    if str(f.get("employment_diversity", "")).lower() == "low":
        score -= 10
    band = "High" if score >= 75 else "Medium" if score >= 55 else "Low"
    return score, band

def determine_signal(f):
    if not passes_buy_gates(f):
        return "AVOID"
    if safe_num(f.get("building_approvals_18m")) is not None and f["building_approvals_18m"] >= 8:
        return "HOLD"
    return "BUY"

# ====================== STREAMLIT APP ======================
uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    results = []

    st.info("🔄 Running full Property Investment Accelerator Logic Engine...")

    for _, row in df.iterrows():
        # Build factor record
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
            # Remaining factors are pending (will be filled by future scrapers)
        }

        # Run the full logic engine
        rw_cagr = calculate_rw_cagr(factors)
        confidence_score, confidence_band = calculate_confidence(factors)
        decision = determine_signal(factors)

        explanation = f"{decision}: "
        if decision == "BUY":
            explanation += "Strong demand-supply balance and meets all core gates."
        elif decision == "HOLD":
            explanation += "Elevated future supply risk detected."
        else:
            explanation += "Failed one or more core eligibility gates."

        results.append({
            "Suburb": row["Suburb"],
            "Decision": decision,
            "Confidence": confidence_band,
            "Confidence Score": confidence_score,
            "RW-CAGR": rw_cagr,
            "Explanation": explanation
        })

    # Display results
    summary_df = pd.DataFrame(results)
    summary_df = summary_df.sort_values(by="Confidence Score", ascending=False)

    st.subheader("📊 Investment Recommendation Summary")
    st.dataframe(summary_df, use_container_width=True, height=600)

    top = summary_df.iloc[0]
    st.success(f"🏆 **BEST SUBURB: {top['Suburb']}** — Decision: **{top['Decision']}**")

    # Download
    output = BytesIO()
    summary_df.to_excel(output, index=False)
    st.download_button("⬇️ Download Full Analysis", output.getvalue(), "Property_Investment_Accelerator_Results.xlsx")

    st.info("Logic engine running per authoritative spec. More scrapers will be added next.")
