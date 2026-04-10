import streamlit as st
import pandas as pd
from io import BytesIO
import requests
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Property Investment Accelerator Matcher",
    layout="wide"
)

st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Base Value auto-scraped from OnTheHouse")

# ====================== COLUMN DEFINITIONS ======================
columns = [
    "State", "Post Code", "Duplicate", "Suburb",
    "Renters Proportion% 15-35%",
    "Vacancy rate% <2%",
    "Auction clearance% >60%",
    "Days on market <55-60",
    "Avg vendor discounting% <5%",
    "Stock on market% <1.3%",
    "12 Months Rolling avg online search interest",
    "Gross rental yield >4%",
    "Demand to Supply Ratio >55%",
    "Statistical reliability >51%",
    "Median 12 months",
    "Typical value",
    "Base Value",
    "Housing affordability",
]

uploaded_file = st.file_uploader(
    "Upload your DSR Excel file",
    type=["xlsx"]
)

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")

    df_clean = pd.DataFrame(columns=columns)

    df_clean["State"] = df["State"]
    df_clean["Post Code"] = df["Post Code"]
    df_clean["Suburb"] = df["Suburb"]
    df_clean["Duplicate"] = df.get("Duplicate", "")

    # -------- DSR Mapping --------
    df_clean["Renters Proportion% 15-35%"] = df["Percent renters in market"].astype(str).str.replace('%','').astype(float)
    df_clean["Vacancy rate% <2%"] = df["Vacancy rate"].astype(str).str.replace('%','').astype(float)
    df_clean["Auction clearance% >60%"] = df["Auction clearance rate"].astype(str).str.replace('%','').astype(float)
    df_clean["Days on market <55-60"] = df["Days on market"].astype(str).str.replace('days','').astype(float)
    df_clean["Avg vendor discounting% <5%"] = df["Avg vendor discount"].astype(str).str.replace('%','').astype(float)
    df_clean["Stock on market% <1.3%"] = df["Percent stock on market"].astype(str).str.replace('%','').astype(float)
    df_clean["12 Months Rolling avg online search interest"] = df["Online search interest"].astype(float)
    df_clean["Gross rental yield >4%"] = df["Gross rental yield"].astype(str).str.replace('%','').astype(float)
    df_clean["Demand to Supply Ratio >55%"] = df["Demand to Supply Ratio"].astype(float)
    df_clean["Statistical reliability >51%"] = df.get("Statistical reliability", 0).astype(float)
    df_clean["Median 12 months"] = df["Median 12 months"].astype(float)
    df_clean["Typical value"] = df["Typical value"].astype(float)
    df_clean["Base Value"] = 0.0
    df_clean["Housing affordability"] = "Pending"

    # ====================== BASE VALUE SCRAPER ======================
    def get_base_value(suburb, state, postcode):
        try:
            slug = suburb.lower().replace(" ", "-")
            url = f"https://www.onthehouse.com.au/property-profile/{state.lower()}/{postcode}/{slug}"
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return 0.0

            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text()
            import re
            numbers = re.findall(r'\$?(\d{1,3}(?:,\d{3})+)', text)
            for num in numbers:
                val = int(num.replace(",", ""))
                if 100_000 <= val <= 2_000_000:
                    return val
            return 0.0
        except:
            return 0.0

    st.info("🔄 Auto-scraping Base Value from OnTheHouse...")

    for idx, row in df_clean.iterrows():
        if df_clean.at[idx, "Base Value"] == 0.0:
            base_val = get_base_value(
                row["Suburb"],
                row["State"],
                row["Post Code"]
            )
            df_clean.at[idx, "Base Value"] = base_val

    st.subheader("✅ Updated Property Investment Accelerator Sheet")
    st.dataframe(df_clean, use_container_width=True, height=600)

    output = BytesIO()
    df_clean.to_excel(output, index=False)
    st.download_button(
        "⬇️ Download Updated Excel",
        output.getvalue(),
        "Property_Investment_Accelerator_Output.xlsx"
    )
``
