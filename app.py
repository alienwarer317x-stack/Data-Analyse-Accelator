import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from engine import evaluate_buy_gates, calculate_confidence

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two‑Stage Discovery + Authoritative Logic Engine")

# ====================== SESSION STATE ======================
if "dsr_discovery_df" not in st.session_state:
    st.session_state.dsr_discovery_df = None
if "explorer_discovery_df" not in st.session_state:
    st.session_state.explorer_discovery_df = None
if "dsr_selected_suburbs" not in st.session_state:
    st.session_state.dsr_selected_suburbs = set()
if "explorer_selected_suburbs" not in st.session_state:
    st.session_state.explorer_selected_suburbs = set()
if "shortlist" not in st.session_state:
    st.session_state.shortlist = []

# ====================== CLIENT MODE ======================
client_mode = st.radio("Client Type", ("DSR Upload", "Explorer"), horizontal=True)

# ====================== STAGE 1 — DISCOVERY FILTERS ======================
st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences Only)")
st.caption("Soft filters only. No investment logic or BUY gates applied here.")
col1, col2 = st.columns(2)
with col1:
    selected_state = st.selectbox(
        "State",
        ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"]
    )
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
with col2:
    max_price = st.slider(
        "Maximum Median Price ($)",
        200_000, 2_000_000, 1_000_000,
        step=50_000
    )
    min_yield = st.slider(
        "Minimum Gross Rental Yield (%)",
        3.0, 8.0, 4.0
    )

# ====================== RESET BUTTON ======================
if st.button("Reset"):
    st.session_state.dsr_discovery_df = None
    st.session_state.explorer_discovery_df = None
    st.session_state.dsr_selected_suburbs = set()
    st.session_state.explorer_selected_suburbs = set()
    st.session_state.shortlist = []

# ====================== NORMALISATION HELPERS ======================
def normalise_plain(val):
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None

def normalise_percent(val):
    if pd.isna(val):
        return None
    try:
        v = float(str(val).replace("%", "").strip())
        return v * 100 if v <= 1 else v
    except:
        return None

# ====================== AUTO-SCRAPERS (SQM + OnTheHouse + HTAG) ======================
def scrape_sqm_10yr_pa(suburb, postcode):
    try:
        url = f"https://sqmresearch.com.au/property-price-growth.php?region={postcode}&type=house"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for text in soup.find_all(string=lambda t: t and "10 Years" in t):
            try:
                val = float(text.strip().replace("%", ""))
                return val
            except:
                continue
        return None
    except:
        return None

def scrape_onthehouse_10yr_total(suburb, postcode):
    try:
        url = f"https://www.onthehouse.com.au/property/{suburb.lower().replace(' ', '-')}-{postcode}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for text in soup.find_all(string=lambda t: t and "10 Years" in t):
            try:
                val = float(text.strip().replace("%", ""))
                return val
            except:
                continue
        return None
    except:
        return None

def scrape_htag_10yr_total(suburb, postcode):
    try:
        url = f"https://www.htag.com.au/{suburb.lower().replace(' ', '-')}-{postcode}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for text in soup.find_all(string=lambda t: t and "10Y" in t):
            try:
                val = float(text.strip().replace("%", ""))
                return val
            except:
                continue
        return None
    except:
        return None

# ====================== RW-CAGR CALCULATION ======================
def calculate_rw_cagr(row):
    sqm_pa = normalise_plain(row.get("SQM 10 years GR% p.a."))
    oth_total = normalise_plain(row.get("Onthehouse 10yrs GR%"))
    htag_total = normalise_plain(row.get("Htag 10 years GR%"))

    # Auto-scrape if missing
    if row.get("Post Code"):
        postcode = str(row.get("Post Code")).strip()
        suburb = str(row.get("Suburb")).strip()
        if sqm_pa is None:
            sqm_pa = scrape_sqm_10yr_pa(suburb, postcode)
        if oth_total is None:
            oth_total = scrape_onthehouse_10yr_total(suburb, postcode)
        if htag_total is None:
            htag_total = scrape_htag_10yr_total(suburb, postcode)

    def to_cagr(total):
        if total is None:
            return None
        return round(((1 + total / 100) ** (1/10) - 1) * 100, 2)

    oth_cagr = to_cagr(oth_total)
    htag_cagr = to_cagr(htag_total)

    values = [v for v in [sqm_pa, oth_cagr, htag_cagr] if v is not None]
    if len(values) == 0:
        return "N/A - no 10yr data"
    return round(sum(values) / len(values), 2)

# ====================== DSR UPLOAD MODE ======================
if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])
    if uploaded_file and st.button("Apply Discovery Filters"):
        df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
        discovered = []
        for _, r in df.iterrows():
            if selected_state != "All" and r.get("State") != selected_state:
                continue
            dom = normalise_plain(str(r.get("Days on market", "")).replace("days", ""))
            price = normalise_plain(r.get("Typical value")) or normalise_plain(r.get("Median 12 months"))
            yld = normalise_percent(r.get("Gross rental yield"))
            if dom is None or dom > max_dom:
                continue
            if price is not None and price > max_price:
                continue
            discovered.append({
                "State": r.get("State"),
                "Suburb": r.get("Suburb"),
                "Post Code": r.get("Post Code"),
                "Median Price": price,
                "Days on Market": dom,
                "Yield %": round(yld, 2) if yld is not None else None,
                "_row": r
            })
        st.session_state.dsr_discovery_df = pd.DataFrame(discovered)

# ====================== EXPLORER MODE ======================
if client_mode == "Explorer" and st.button("Apply Discovery Filters"):
    demo_data = [
        {"State": "NSW", "Suburb": "Grafton", "Post Code": "2460", "Median Price": 520000, "Days on Market": 39, "Yield %": 5.34, "_row": {}},
    ]
    df = pd.DataFrame(demo_data)
    df = df[(df["Median Price"] <= max_price) & (df["Days on Market"] <= max_dom)]
    st.session_state.explorer_discovery_df = df

# ====================== STAGE 1 RESULTS — SINGLE TABLE ======================
current_discovery_df = None
current_selected_suburbs = set()
if client_mode == "DSR Upload" and st.session_state.dsr_discovery_df is not None and not st.session_state.dsr_discovery_df.empty:
    current_discovery_df = st.session_state.dsr_discovery_df
    current_selected_suburbs = st.session_state.dsr_selected_suburbs
elif client_mode == "Explorer" and st.session_state.explorer_discovery_df is not None and not st.session_state.explorer_discovery_df.empty:
    current_discovery_df = st.session_state.explorer_discovery_df
    current_selected_suburbs = st.session_state.explorer_selected_suburbs

if current_discovery_df is not None and not current_discovery_df.empty:
    st.markdown("## 📍 Discovery Results")
    df_display = current_discovery_df.copy()
    df_display["Median Price"] = df_display["Median Price"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
    st.dataframe(df_display[["State", "Suburb", "Median Price", "Days on Market", "Yield %"]], use_container_width=True)

    all_suburbs = current_discovery_df["Suburb"].tolist()
    selected = st.multiselect(
        "Select suburbs for Deep Analysis",
        options=all_suburbs,
        default=list(current_selected_suburbs)
    )
    if client_mode == "DSR Upload":
        st.session_state.dsr_selected_suburbs = set(selected)
        current_selected_suburbs = st.session_state.dsr_selected_suburbs
    else:
        st.session_state.explorer_selected_suburbs = set(selected)
        current_selected_suburbs = st.session_state.explorer_selected_suburbs

# ====================== STAGE 2 — DEEP ANALYSIS ======================
if current_selected_suburbs:
    st.markdown("## 🟥 Stage 2 — Deep Analysis (Authoritative Engine)")
    if st.button("Run Deep Analysis on Selected Suburbs"):
        results = []
        for _, r in current_discovery_df.iterrows():
            if r["Suburb"] not in current_selected_suburbs:
                continue
            row = r["_row"]
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
            rw_cagr = calculate_rw_cagr(row)

            results.append({
                "Suburb": r["Suburb"],
                "Decision": decision,
                "Confidence": band,
                "Confidence Score": score,
                "Failed Gates": ", ".join(failed) if failed else "None",
                "RW-CAGR": rw_cagr
            })
        st.subheader("✅ Deep Analysis Results")
        st.dataframe(pd.DataFrame(results), use_container_width=True)

# ====================== SHORTLIST ======================
if st.session_state.get("shortlist"):
    st.markdown("## 📋 Shortlist")
    st.write(st.session_state.shortlist)

st.caption("Property Investment Accelerator — Authoritative Logic Engine")
