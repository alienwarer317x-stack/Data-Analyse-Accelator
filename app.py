import streamlit as st
import pandas as pd
from engine import evaluate_suburb

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
st.caption("Soft filters only. No investment logic applied here.")

col1, col2 = st.columns(2)
with col1:
    selected_state = st.selectbox(
        "State", ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"]
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

# ====================== COLUMN NORMALISATION ======================
def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Days on market": "Days on Market",
        "Median 12 months": "Median Price",
        "Typical value": "Median Price",
        "Typical Value": "Median Price",
        "Gross rental yield": "Yield %",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

# ====================== DISCOVERY FILTER ======================
def filter_df(df, state, max_dom, max_price, min_yield):
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    if "Days on Market" not in df.columns or "Median Price" not in df.columns:
        return pd.DataFrame()

    df["Days on Market"] = pd.to_numeric(df["Days on Market"], errors="coerce")
    df["Median Price"] = pd.to_numeric(df["Median Price"], errors="coerce")

    if "Yield %" in df.columns:
        df["Yield %"] = pd.to_numeric(df["Yield %"], errors="coerce")
    else:
        df["Yield %"] = float("nan")

    filtered = df[
        (df["Days on Market"] <= max_dom) &
        (df["Median Price"] <= max_price) &
        (df["Yield %"] >= min_yield)
    ]

    if state != "All":
        filtered = filtered[filtered["State"] == state]

    return filtered

# ====================== DSR UPLOAD ======================
if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])
    if uploaded_file and st.button("Apply Discovery Filters"):
        df = pd.read_excel(uploaded_file)
        df = normalise_columns(df)
        st.session_state.dsr_discovery_df = filter_df(
            df, selected_state, max_dom, max_price, min_yield
        )

# ====================== EXPLORER MODE ======================
if client_mode == "Explorer" and st.button("Apply Discovery Filters"):
    try:
        df = pd.read_csv("explorer_data.csv")
    except FileNotFoundError:
        st.error("Explorer data file not found.")
        st.stop()

    st.session_state.explorer_discovery_df = filter_df(
        df, selected_state, max_dom, max_price, min_yield
    )

# ====================== STAGE 1 RESULTS ======================
if client_mode == "DSR Upload":
    current_df = st.session_state.dsr_discovery_df
    current_selected = st.session_state.dsr_selected_suburbs
else:
    current_df = st.session_state.explorer_discovery_df
    current_selected = st.session_state.explorer_selected_suburbs

if current_df is not None and not current_df.empty:
    st.markdown(f"## 📍 Discovery Results ({len(current_df)} suburbs)")

    df_display = current_df.copy()
    df_display["Median Price"] = df_display["Median Price"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else ""
    )

    st.dataframe(
        df_display[["State", "Suburb", "Median Price", "Days on Market", "Yield %"]],
        use_container_width=True
    )

    suburbs = current_df["Suburb"].tolist()
    selected = st.multiselect(
        "Select suburbs for Deep Analysis",
        options=suburbs,
        default=list(current_selected)
    )

    if client_mode == "DSR Upload":
        st.session_state.dsr_selected_suburbs = set(selected)
    else:
        st.session_state.explorer_selected_suburbs = set(selected)

# ====================== STAGE 2 — AUTHORITATIVE ENGINE ======================
selected_suburbs = (
    st.session_state.dsr_selected_suburbs
    if client_mode == "DSR Upload"
    else st.session_state.explorer_selected_suburbs
)

if selected_suburbs:
    st.markdown("## 🟥 Stage 2 — Deep Analysis (Authoritative Engine)")

    if st.button("Run Deep Analysis"):
        results = []

        for _, r in current_df.iterrows():
            if r["Suburb"] not in selected_suburbs:
                continue

            if "_row" not in r or not isinstance(r["_row"], dict):
                st.error(f"Missing or invalid _row snapshot for {r['Suburb']}")
                continue

            analysis = evaluate_suburb(r["_row"])
            analysis["Suburb"] = r["Suburb"]
            results.append(analysis)

        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True)

# ====================== SHORTLIST ======================
if st.session_state.shortlist:
    st.markdown("## 📋 Shortlist")
    st.write(st.session_state.shortlist)

st.caption("Property Investment Accelerator — Authoritative Logic Engine")
