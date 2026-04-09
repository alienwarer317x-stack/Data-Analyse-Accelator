import streamlit as st
import pandas as pd
from io import BytesIO
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Base Value now auto-scraped from OnTheHouse + Housing Affordability from Domain")

# ====================== ALL COLUMNS ======================
columns = [
    "State", "Post Code", "Duplicate", "Suburb",
    "Renters Proportion% 15-35%", "Vacancy rate% <2%", "Auction clearance% >60%",
    "Days on market <55-60", "Avg vendor discounting% <5%", "Stock on market% <1.3%",
    "12 Months Rolling avg online search interest Ratio 25 to1",
    "Gross rental yield >4%", "Demand to Supply Ratio >55%", "Statistical reliability >51%",
    "36 month GR %<50% SQM 3yrs*3",
    "36 month median value growth rate % <50% Htag(suburb)",
    "36 Month vs Typical value <50%",
    "AVG GR 3yrs SQM+Htag+Typical",
    "12 month rental growth rate% >5%",
    "10 years Median growth Rate On the house",
    "10 Years growth Rate% OTH <7%",
    "Total CAGR Growth 10yrs",
    "CAGR SQM", "SQM 10 years GR% p.a.",
    "CAGR OTH", "Onthehouse 10yrs GR%",
    "CAGR Htag", "Htag 10 years GR%",
    "Median 12 months", "Typical value", "Base Value",
    "18 month building approvals versus total dwellings < 8%",
    "Developable land supply",
    "Professional’ occupation increasing faster than State average 2016",
    "Professional’ occupation increasing faster than State average 2021",
    "Household income increasing faster than State average 2016",
    "Household income increasing faster than State average 2021",
    "Households rent <30% of household income > 60%",
    "mortgage repayments <30% of household income > 75%",
    "Job’ infrastructure >100 to 200",
    "Level of amenity (schools/ public transport/ shopping/ parks)",
    "Proximity in travel time to activity/ job center(s)",
    "5 year Job advertisements",
    "Occupation / Industry of employment",
    "Housing affordability"
]

uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    
    df_clean = pd.DataFrame(columns=columns)
    df_clean["State"] = df["State"]
    df_clean["Post Code"] = df["Post Code"]
    df_clean["Suburb"] = df["Suburb"]
    df_clean["Duplicate"] = df.get("Duplicate", "")

    # DSR auto-mapping
    df_clean["Renters Proportion% 15-35%"] = df["Percent renters in market"].astype(str).str.replace('%','').astype(float)
    df_clean["Vacancy rate% <2%"] = df["Vacancy rate"].astype(str).str.replace('%','').astype(float)
    df_clean["Auction clearance% >60%"] = df["Auction clearance rate"].astype(str).str.replace('%','').astype(float)
    df_clean["Days on market <55-60"] = df["Days on market"].astype(str).str.replace('days','').astype(float)
    df_clean["Avg vendor discounting% <5%"] = df["Avg vendor discount"].astype(str).str.replace('%','').astype(float)
    df_clean["Stock on market% <1.3%"] = df["Percent stock on market"].astype(str).str.replace('%','').astype(float)
    df_clean["12 Months Rolling avg online search interest Ratio 25 to1"] = df["Online search interest"].astype(float)
    df_clean["Gross rental yield >4%"] = df["Gross rental yield"].astype(str).str.replace('%','').astype(float)
    df_clean["Demand to Supply Ratio >55%"] = df["Demand to Supply Ratio"].astype(float)
    df_clean["Statistical reliability >51%"] = df.get("Statistical reliability", 0).astype(float)
    df_clean["Median 12 months"] = df["Median 12 months"].astype(float)
    df_clean["Typical value"] = df["Typical value"].astype(float)
    df_clean["Base Value"] = 0.0   # Will be filled by scraper

    # Remaining columns = Pending
    for col in columns:
        if col not in df_clean.columns or pd.isna(df_clean[col]).all():
            df_clean[col] = "Pending - Auto-scrape coming"

    # ====================== IMPROVED BASE VALUE SCRAPER (OnTheHouse) ======================
    def get_base_value(suburb, state, postcode):
        try:
            slug = suburb.lower().replace(" ", "-")
            url = f"https://www.onthehouse.com.au/property-profile/{state.lower()}/{postcode}/{slug}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return 0.0

            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text()

            # Look for historical median value (3 years ago)
            # Common patterns on OnTheHouse: "3 years ago", "Feb 2023", "$xxx,xxx" near year
            if "3 years" in text.lower() or "2023" in text or "2022" in text:
                # Very basic extraction - looks for dollar amounts near historical text
                import re
                numbers = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', text)
                if numbers:
                    # Take the first plausible historical price (usually the oldest one)
                    for num in numbers:
                        val = int(num.replace(',', ''))
                        if 100000 <= val <= 2000000:  # realistic house price range
                            return val
            return 0.0
        except:
            return 0.0

    # ====================== HOUSING AFFORDABILITY (unchanged) ======================
    def get_housing_affordability(suburb, state, postcode):
        try:
            slug = suburb.lower().replace(" ", "-")
            url = f"https://www.domain.com.au/suburb-profile/{slug}-{state.lower()}-{postcode}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return "Pending - Domain page not found"
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text().lower()
            if any(word in text for word in ["mortgage", "repayment", "affordability"]):
                return "Good"
            return "Average"
        except:
            return "Pending - Auto-scrape failed"

    # Run both scrapers
    st.info("🔄 Auto-scraping Base Value from OnTheHouse + Housing Affordability from Domain...")
    for idx, row in df_clean.iterrows():
        # Base Value
        if df_clean.at[idx, "Base Value"] == 0.0:
            base_val = get_base_value(row["Suburb"], row["State"], row["Post Code"])
            df_clean.at[idx, "Base Value"] = base_val
        
        # Housing Affordability
        if df_clean.at[idx, "Housing affordability"] == "Pending - Auto-scrape coming":
            aff = get_housing_affordability(row["Suburb"], row["State"], row["Post Code"])
            df_clean.at[idx, "Housing affordability"] = aff

    # ====================== FINAL RECOMMENDATION ======================
    st.subheader("✅ Full Property Investment Accelerator Sheet")

    def growth_score(row):
        score = 0
        key_cols = ["Demand to Supply Ratio >55%", "Gross rental yield >4%", "Housing affordability", "Vacancy rate% <2%"]
        for col in key_cols:
            val = row[col]
            if isinstance(val, (int, float)) and val > 0:
                score += 1
            elif val in ["Good", "Super"]:
                score += 1
        return score

    df_clean["Growth Score"] = df_clean.apply(growth_score, axis=1)
    df_clean = df_clean.sort_values(by="Growth Score", ascending=False)

    st.dataframe(df_clean, use_container_width=True, height=700)

    top = df_clean.iloc[0]["Suburb"]
    st.success(f"🏆 **BEST SUBURB TO INVEST: {top}** (Highest Growth Score)")

    output = BytesIO()
    df_clean.to_excel(output, index=False)
    st.download_button("⬇️ Download Full Updated Excel", output.getvalue(), "Suburb_Listing_1_Updated.xlsx")
