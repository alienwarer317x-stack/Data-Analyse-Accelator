import streamlit as st
import pandas as pd
from io import BytesIO
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Full Authoritative Logic Engine + DSR Upload")

# ====================== BUY GATES (from your spec) ======================
BUY_GATES = {
    "renters_pct": (15, 35),
    "vacancy_pct": "<2",
    "demand_supply_ratio": ">55",
    "stock_on_market_pct": "<1.3",
    "gross_rental_yield": ">4",
    "statistical_reliability": ">51"
}

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

def safe_num(v):
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except:
        return None

# ====================== LOGIC ENGINE (from your authoritative spec) ======================
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
    # Check all BUY gates
    if (f.get("renters_pct") is None or not (15 <= f["renters_pct"] <= 35) or
        f.get("vacancy_pct") is None or f["vacancy_pct"] >= 2 or
        f.get("demand_supply_ratio") is None or f["demand_supply_ratio"] <= 55 or
        f.get("stock_on_market_pct") is None or f["stock_on_market_pct"] >= 1.3 or
        f.get("gross_rental_yield") is None or f["gross_rental_yield"] <= 4 or
        f.get("statistical_reliability") is None or f["statistical_reliability"] <= 51):
        return "AVOID"
    if safe_num(f.get("building_approvals_18m")) is not None and f["building_approvals_18m"] >= 8:
        return "HOLD"
    return "BUY"

# ====================== MAIN APP ======================
uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    results = []

    st.info("🔄 Running full Property Investment Accelerator Logic Engine...")

    for _, row in df.iterrows():
        # ==================== FIXED DSR MAPPING ====================
        factors = {
            "renters_pct": normalise_percent(row.get("Percent renters in market")),
            "vacancy_pct": normalise_plain(row.get("Vacancy rate")),
            "demand_supply_ratio": normalise_plain(row.get("Demand to Supply Ratio")),
            "stock_on_market_pct": normalise_plain(row.get("Percent stock on market")),
            "days_on_market": normalise_plain(str(row.get("Days on market", "")).replace("days", "")),
            "auction_clearance_pct": normalise_plain(row.get("Auction clearance rate")),
            "vendor_discount_pct": normalise_plain(row.get("Avg vendor discount")),
            "gross_rental_yield": normalise_percent(row.get("Gross rental yield")),
            "statistical_reliability": normalise_plain(row.get("Statistical reliability")),
            "median_12m_change": normalise_plain(row.get("Median 12 months")),
            "typical_value": normalise_plain(row.get("Typical value")),
            # Scraped fields (currently None - will be filled later)
            "sqm_cagr_10y": None,
            "oth_10y_growth": None,
            "htag_cagr_10y": None,
            "building_approvals_18m": None,
            "employment_diversity": None,
        }

        # ==================== RUN LOGIC ENGINE ====================
        rw_cagr = calculate_rw_cagr(factors)
        confidence_score, confidence_band = calculate_confidence(factors)
        decision = determine_signal(factors)

        explanation = f"{decision}: "
        if decision == "BUY":
            explanation += "Meets all core eligibility gates."
        elif decision == "HOLD":
            explanation += "Elevated future supply risk."
        else:
            explanation += "Failed one or more core eligibility gates."

        results.append({
            "Suburb": row.get("Suburb"),
            "Decision": decision,
            "Confidence": confidence_band,
            "Confidence Score": confidence_score,
            "RW-CAGR": rw_cagr,
            "Demand to Supply Ratio": factors["demand_supply_ratio"],
            "Vacancy %": factors["vacancy_pct"],
            "Gross Yield %": factors["gross_rental_yield"],
            "Explanation": explanation
        })

    # ====================== DISPLAY ======================
    summary_df = pd.DataFrame(results)
    summary_df = summary_df.sort_values(by=["Decision", "Confidence Score"], ascending=[False, False])

    st.subheader("📊 Investment Recommendation Summary")
    st.dataframe(summary_df, use_container_width=True, height=700)

    if not summary_df.empty:
        top = summary_df.iloc[0]
        st.success(f"🏆 **BEST SUBURB: {top['Suburb']}** — Decision: **{top['Decision']}**")

    output = BytesIO()
    summary_df.to_excel(output, index=False)
    st.download_button("⬇️ Download Full Analysis", output.getvalue(), "Property_Investment_Accelerator_Results.xlsx")

    st.info("✅ Full logic engine active. More auto-scrapers will be added next.")
