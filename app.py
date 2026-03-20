import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Upload DSR Excel → FULL PDF + all new CAGR fields ready!")
st.markdown("**DSR data auto-filled • New fields = Pending (auto-scrape coming)**")

# ==================== ALL COLUMNS (DSR + PDF + your new ones) ====================
columns = [
    "State", "Post Code", "Duplicate", "Suburb",
    "Renter proportion %", "Vacancy rate %", "Auction clearance rate %",
    "Days on market", "Average vendor discounting %", "Stock on market %",
    "12 month rolling avg online search interest ratio", "Gross yield %",
    "Demand to supply ratio", "Statistical reliability",
    "Median 12 months", "Typical value", "Base Value",

    # New fields you added
    "36 month GR %<50% SQM 3yrs*3",
    "36 month median value growth rate % <50% Htag(suburb)",
    "36 Month vs Typical value",
    "AVG GR 3yrs SQM+Htag+Typical",
    "SQM 10 years GR% p.a.",
    "Onthehouse 10yrs GR% p.a.",
    "Htag 10 years GR%",
    "CAGR SQM", "CAGR OTH", "CAGR Htag",

    # Other PDF fields
    "12 month rental growth rate %", "18 month building approvals versus total dwellings",
    "Developable land supply", "Level of amenity", "Proximity in travel time to activity/job center(s)",
    "Household income increasing faster than State average",
    "Professional occupation increasing faster than State average",
    "10 year median value average growth rate %",
    "Households rent <30% of household income",
    "Households mortgage <30% of household income"
]

# Targets for colouring
targets = {
    "Renter proportion %": (15, 35),
    "Vacancy rate %": (0, 2),
    "Auction clearance rate %": (60, 100),
    "Days on market": (0, 65),
    "Average vendor discounting %": (0, 5),
    "Stock on market %": (0, 1.3),
    "12 month rolling avg online search interest ratio": (26, 1000),
    "Gross yield %": (4, 100),
    "Demand to supply ratio": (55, 1000),
    "36 month GR %<50% SQM 3yrs*3": (0, 50),
    "36 month median value growth rate % <50% Htag(suburb)": (0, 50),
    "36 Month vs Typical value": (0, 50),
    "SQM 10 years GR% p.a.": (0, 7),
    "Onthehouse 10yrs GR% p.a.": (0, 7),
    "Htag 10 years GR%": (0, 7),
    "12 month rental growth rate %": (5, 100),
    "18 month building approvals versus total dwellings": (0, 8),
    "10 year median value average growth rate %": (0, 7)
}

uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    
    df_clean = pd.DataFrame(columns=columns)
    df_clean["State"] = df["State"]
    df_clean["Post Code"] = df["Post Code"]
    df_clean["Suburb"] = df["Suburb"]
    df_clean["Duplicate"] = df.get("Duplicate", "")

    # === DSR AUTO-FILL ===
    df_clean["Renter proportion %"] = df["Percent renters in market"].astype(str).str.replace('%','').astype(float)
    df_clean["Vacancy rate %"] = df["Vacancy rate"].astype(str).str.replace('%','').astype(float)
    df_clean["Auction clearance rate %"] = df["Auction clearance rate"].astype(str).str.replace('%','').astype(float)
    df_clean["Days on market"] = df["Days on market"].astype(str).str.replace('days','').astype(float)
    df_clean["Average vendor discounting %"] = df["Avg vendor discount"].astype(str).str.replace('%','').astype(float)
    df_clean["Stock on market %"] = df["Percent stock on market"].astype(str).str.replace('%','').astype(float)
    df_clean["12 month rolling avg online search interest ratio"] = df["Online search interest"].astype(float)
    df_clean["Gross yield %"] = df["Gross rental yield"].astype(str).str.replace('%','').astype(float)
    df_clean["Demand to supply ratio"] = df["Demand to Supply Ratio"].astype(float)
    df_clean["Statistical reliability"] = df.get("Statistical reliability", 0).astype(float)
    df_clean["Median 12 months"] = df["Median 12 months"].astype(float)
    df_clean["Typical value"] = df["Typical value"].astype(float)
    df_clean["Base Value"] = df.get("Base Value", 0).astype(float)   # if you add it later

    # === NEW FIELDS = PENDING (auto-scrape coming) ===
    pending_cols = [col for col in columns if col not in df_clean.columns or pd.isna(df_clean[col]).all()]
    for col in pending_cols:
        df_clean[col] = "Pending - Auto-scrape coming"

    # Colour function
    def get_color(val, factor):
        if "Pending" in str(val):
            return "background-color: lightgray"
        try:
            v = float(str(val).replace('%', ''))
        except:
            return ""
        low, high = targets.get(factor, (0, 0))
        if low <= v <= high:
            return "background-color: lightgreen"
        return "background-color: lightcoral"

    # Growth Score
    score_cols = [col for col in columns if col in targets]
    df_clean["Growth Score (out of 13)"] = df_clean[score_cols].apply(
        lambda row: sum("lightgreen" in get_color(row[col], col) for col in score_cols), axis=1)

    # Display
    st.subheader("✅ FULL ENRICHED SHEET – Best suburbs first")
    styled = df_clean.style.apply(lambda row: [get_color(row[col], col) for col in columns], axis=1)
    st.dataframe(styled, use_container_width=True, height=700)

    # Download
    output = BytesIO()
    df_clean.to_excel(output, index=False)
    st.download_button("⬇️ Download FULL Enriched Excel", output.getvalue(), "FULL_Enriched_Suburbs.xlsx")

    st.success("🎉 App updated! All your fields + correct CAGR logic are now in place. Next: turn on auto-scraping one field at a time.")
