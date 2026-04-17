from engine import evaluate_suburb
from ingestion.sqm_adapter import build_row_from_sqm
from ingestion.dsr_adapter import build_row_from_dsr
import streamlit as st
import pandas as pd
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
            price = (
                normalise_plain(r.get("Typical value"))
                or normalise_plain(r.get("Median 12 months"))
            )
            yld = normalise_percent(r.get("Gross rental yield"))

            if dom is None or dom > max_dom:
                continue
            if price is not None and price > max_price:
                continue

            discovered.append({
                "State": r.get("State"),
                "Suburb": r.get("Suburb"),
                "Median Price": price,
                "Days on Market": dom,
                "Yield %": round(yld, 2) if yld is not None else None,
                "_row": build_row_from_dsr(r)
            })

        st.session_state.dsr_discovery_df = pd.DataFrame(discovered)

# ====================== EXPLORER MODE ======================
if client_mode == "Explorer" and st.button("Apply Discovery Filters"):
    demo_data = [
        {"State": "NSW", "Suburb": "Grafton", "Median Price": 520000, "Days on Market": 39, "Yield %": 5.34, "_row": {}},
        {"State": "QLD", "Suburb": "Norville", "Median Price": 570000, "Days on Market": 43, "Yield %": 5.08, "_row": {}},
    ]

    df = pd.DataFrame(demo_data)
    df = df[(df["Median Price"] <= max_price) & (df["Days on Market"] <= max_dom)]
    st.session_state.explorer_discovery_df = df

# ====================== STAGE 1 RESULTS ======================
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

    st.dataframe(
        df_display[["State", "Suburb", "Median Price", "Days on Market", "Yield %"]],
        use_container_width=True
    )

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

            if client_mode == "DSR Upload":
                row = r["_row"]
            else:
                row = build_row_from_sqm(
                    state=r.get("State"),
                    suburb=r.get("Suburb")
                )

            analysis = evaluate_suburb({
                **row,
                "State": r.get("State"),
                "Suburb": r.get("Suburb")
            })

            results.append({
                "Suburb": r["Suburb"],
                "Decision": analysis["Decision"],
                "Confidence": analysis["Confidence"],
                "Confidence Score": analysis["Confidence Score"],
                "Investability Score": analysis["Investability Score"],
                "Failed Gates": ", ".join(analysis["Failed Gates"]),
                "Narrative": analysis["Narrative"],
            })

        st.subheader("✅ Deep Analysis Results")
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(
            by="Investability Score",
            ascending=False
        )
        
# ✅ STEP 2B-1: Split BUY vs AVOID (BUY-first portfolio view)
df_buy = df_results[df_results["Decision"] == "BUY"]
df_avoid = df_results[df_results["Decision"] == "AVOID"]

# ✅ STEP 2B-2: BUY section
st.markdown("### 🏆 Top BUY Opportunities")

st.dataframe(
    df_buy[
        [
            "Suburb",
            "Decision",
            "Confidence",
            "Confidence Score",
            "Investability Score",
            "Failed Gates",
        ]
    ],
    use_container_width=True
    )

# ✅ STEP 2B-2: AVOID section
st.markdown("### ⚠️ AVOID / Watchlist Suburbs")

st.dataframe(
    df_avoid[
        [
            "Suburb",
            "Decision",
            "Confidence",
            "Confidence Score",
            "Investability Score",
            "Failed Gates",
        ]
    ],
    use_container_width=True
    )

st.subheader("🧠 Investment Rationale")

        for res in results:
            narrative = res["Narrative"]

            with st.expander(narrative["headline"]):

                if narrative["strengths"]:
                    st.markdown("### ✅ Strengths")
                    for s in narrative["strengths"]:
                        st.markdown(f"- {s}")

                if narrative["risks"]:
                    st.markdown("### ⚠️ Risks")
                    for r in narrative["risks"]:
                        st.markdown(f"- {r}")

                if narrative["failed_gate_explanations"]:
                    st.markdown("### ❌ Failed Investment Criteria")
                    for g in narrative["failed_gate_explanations"]:
                        st.markdown(f"- {g}")
                        
                if narrative.get("path_to_buy"):
                    st.markdown("### 🔁 What would need to change to become a BUY")
                    for action in narrative["path_to_buy"]:
                        st.markdown(f"- {action}")
