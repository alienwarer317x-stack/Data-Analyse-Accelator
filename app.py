import streamlit as st
import pandas as pd
from engine import evaluate_suburb  # Your new engine.py

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two-Stage Discovery + Authoritative Logic Engine")

# Session state
for key in ["dsr_discovery_df", "explorer_discovery_df", "dsr_selected_suburbs", "explorer_selected_suburbs", "shortlist"]:
    if key not in st.session_state:
        st.session_state[key] = None if "df" in key else set()

client_mode = st.radio("Client Type", ("DSR Upload", "Explorer"), horizontal=True)

# Stage 1 Filters
st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences Only)")
col1, col2 = st.columns(2)
with col1:
    state = st.selectbox("State", ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"])
    max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
with col2:
    max_price = st.slider("Maximum Median Price ($)", 200_000, 2_000_000, 1_000_000, step=50_000)
    min_yield = st.slider("Minimum Gross Rental Yield (%)", 3.0, 8.0, 4.0)

def normalise_columns(df):
    rename_map = {
        "Days on market": "Days on Market",
        "Median 12 months": "Median Price",
        "Typical value": "Median Price",
        "Typical Value": "Median Price",
        "Gross rental yield": "Yield %",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

def add_row_snapshot(df):
    """Adds _row dict with raw data for engine."""
    df["_row"] = df.apply(lambda row: row.to_dict(), axis=1)
    return df

def filter_df(df, state, max_dom, max_price, min_yield):
    if df is None or df.empty:
        return pd.DataFrame()
    df = normalise_columns(df)
    df = df.copy()
    
    # Safe numeric conversion
    for col in ["Days on Market", "Median Price", "Yield %"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            df[col] = 0 if col != "Yield %" else float('nan')
    
    # Visibility filters only
    filtered = df[
        (df["Days on Market"] <= max_dom) &
        (df["Median Price"] <= max_price) &
        (df["Yield %"] >= min_yield)
    ].copy()
    
    if state != "All" and "State" in filtered:
        filtered = filtered[filtered["State"] == state]
    
    return add_row_snapshot(filtered)  # FIXED: Engine-ready

# Data loading & filtering (auto on change)
if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload DSR Excel", type="xlsx")
    if uploaded_file:
        df_raw = pd.read_excel(uploaded_file)
        st.session_state.dsr_discovery_df = filter_df(df_raw, state, max_dom, max_price, min_yield)
    current_df = st.session_state.dsr_discovery_df
    current_selected = st.session_state.dsr_selected_suburbs
else:  # Explorer
    if st.session_state.explorer_discovery_df is None:
        try:
            df_raw = pd.read_csv("explorer_data.csv")
            st.session_state.explorer_discovery_df = filter_df(df_raw, state, max_dom, max_price, min_yield)
        except FileNotFoundError:
            st.error("explorer_data.csv missing.")
            st.stop()
    current_df = st.session_state.explorer_discovery_df
    current_selected = st.session_state.explorer_selected_suburbs

# Stage 1 Results
if current_df is not None and not current_df.empty:
    st.markdown(f"## 📍 Discovery Results ({len(current_df)} suburbs)")
    
    df_display = current_df.copy()
    if "Median Price" in df_display:
        df_display["Median Price"] = df_display["Median Price"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
    display_cols = ["State", "Suburb", "Median Price", "Days on Market", "Yield %"]
    avail_cols = [c for c in display_cols if c in df_display.columns]
    st.dataframe(df_display[avail_cols], use_container_width=True)
    
    suburbs = current_df["Suburb"].tolist()
    selected = st.multiselect("Select for Deep Analysis", options=suburbs, default=list(current_selected))
    
    # Update session
    if client_mode == "DSR Upload":
        st.session_state.dsr_selected_suburbs = set(selected)
    else:
        st.session_state.explorer_selected_suburbs = set(selected)

# Stage 2 - Auto-runs (no button needed)
selected_suburbs = st.session_state.dsr_selected_suburbs if client_mode == "DSR Upload" else st.session_state.explorer_selected_suburbs
if selected_suburbs and current_df is not None:
    st.markdown("## 🟥 Stage 2 — Authoritative Engine")
    results = []
    for suburb in selected_suburbs:
        row = current_df[current_df["Suburb"] == suburb]
        if row.empty:
            continue
        row = row.iloc[0]
        if "_row" not in row or not isinstance(row["_row"], dict):
            st.error(f"Invalid _row for {suburb}")
            continue
        
        analysis = evaluate_suburb(row["_row"])
        analysis["Suburb"] = suburb
        results.append(analysis)
    
    if results:
        results_df = pd.DataFrame(results)
        st.dataframe(results_df, use_container_width=True)

# Shortlist
if st.session_state.shortlist:
    st.markdown("## 📋 Shortlist")
    st.write(list(st.session_state.shortlist))

st.caption("Property Investment Accelerator — Locked Architecture")
