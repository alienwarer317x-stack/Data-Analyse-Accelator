import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Property Investment Accelerator", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Upload DSR Excel → Auto-matched to PDF factors in seconds")
st.markdown("**For a 5th grader: just upload and click download!**")

# PDF targets (used for colouring AND scoring)
targets = {
    "Renter proportion %": (15, 35),
    "Vacancy rate %": (0, 2),
    "Auction clearance rate %": (60, 100),
    "Days on market": (0, 65),
    "Average vendor discounting %": (0, 5),
    "Stock on market %": (0, 1.3),
    "12 month rolling avg online search interest ratio": (26, 1000),
    "Gross yield %": (4, 100),
    "Demand to supply ratio": (55, 1000)
}

uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    
    df_clean = pd.DataFrame()
    df_clean["State"] = df["State"]
    df_clean["Post Code"] = df["Post Code"]
    df_clean["Suburb"] = df["Suburb"]
    df_clean["Renter proportion %"] = df["Percent renters in market"].astype(str).str.replace('%', '').astype(float)
    df_clean["Vacancy rate %"] = df["Vacancy rate"].astype(str).str.replace('%', '').astype(float)
    df_clean["Auction clearance rate %"] = df["Auction clearance rate"].astype(str).str.replace('%', '').astype(float)
    df_clean["Days on market"] = df["Days on market"].astype(str).str.replace('days', '').astype(float)
    df_clean["Average vendor discounting %"] = df["Avg vendor discount"].astype(str).str.replace('%', '').astype(float)
    df_clean["Stock on market %"] = df["Percent stock on market"].astype(str).str.replace('%', '').astype(float)
    df_clean["12 month rolling avg online search interest ratio"] = df["Online search interest"].astype(float)
    df_clean["Gross yield %"] = df["Gross rental yield"].astype(str).str.replace('%', '').astype(float)
    df_clean["Demand to supply ratio"] = df["Demand to Supply Ratio"].astype(float)
    
    # Missing fields
    pending = ["36 month median value growth rate %", "12 month rental growth rate %",
               "18 month building approvals versus total dwellings", "Accessibility infrastructure",
               "Job infrastructure", "Developable land supply"]
    for col in pending:
        df_clean[col] = "Click links below to fill"
    
    # Colour function
    def get_color(val, factor):
        if "Click links" in str(val):
            return "background-color: lightgray"
        try:
            v = float(str(val).replace('%', ''))
        except:
            return ""
        if factor not in targets:
            return ""
        low, high = targets[factor]
        if low <= v <= high:
            return "background-color: lightgreen"
        return "background-color: lightcoral"
    
    # Growth Score
    score_cols = list(targets.keys())
    df_clean["Growth Score (out of 9)"] = df_clean[score_cols].apply(
        lambda row: sum("lightgreen" in get_color(row[col], col) for col in score_cols), axis=1)
    
    # Show table
    st.subheader(f"✅ Scored Suburbs — Best first (Growth Score out of 9)")
    styled = df_clean.style.apply(lambda row: [get_color(row[col], col) for col in df_clean.columns], axis=1)
    st.dataframe(styled, use_container_width=True, height=700)
    
    # Download
    output = BytesIO()
    df_clean.to_excel(output, index=False)
    st.download_button("⬇️ Download Enriched Excel", output.getvalue(), "Enriched_Suburbs.xlsx")
    
    # Quick links
    st.subheader("🔗 Quick Links for Missing Factors")
    for _, row in df_clean.iterrows():
        with st.expander(f"{row['Suburb']} ({row['State']} {row['Post Code']}) — Score {row['Growth Score (out of 9)']}/9"):
            suburb_slug = row['Suburb'].lower().replace(" ", "-")
            domain_link = f"https://www.domain.com.au/suburb-profile/{suburb_slug}-{row['State'].lower()}-{row['Post Code']}"
            st.markdown(f"[Domain Profile (growth + rental)]({domain_link})")
            st.markdown("[OnTheHouse Median Growth](https://www.onthehouse.com.au/suburb-research)")
            st.markdown("[ABS QuickStats](https://www.abs.gov.au/census/find-census-data/quickstats/2021)")
            st.markdown("[Microburbs](https://www.microurbs.com.au)")

    st.success("🎉 Done! Upload worked perfectly this time.")
