from ingestion.scoring import score_row
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

# inside app.py Explorer branch
if client_mode == "Explorer":
    st.markdown("## Explorer Mode")
    url_input = st.text_input("Enter listing or data URL to fetch metrics")
    suburb_input = st.text_input("Suburb name (optional)")
    if st.button("Fetch and Score"):
        with st.spinner("Fetching data and scoring..."):
            sqm_source = {"url": url_input, "suburb": suburb_input}
            row = build_row_from_sqm(sqm_source)
            if row.get("scrape_error"):
                st.error(f"Scrape error: {row['scrape_error']}")
            else:
                # canonicalise if you have the function in validation
                from ingestion.validation import _canonicalise_df
                import pandas as pd
                df_tmp, mapping = _canonicalise_df(pd.DataFrame([row]))
                from ingestion.scoring import score_row
                s, label = score_row(df_tmp.iloc[0].to_dict())
                st.metric("Score", f"{s:.1f}", delta=None)
                st.success(f"Decision: {label}")
                st.dataframe(df_tmp)

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

    # ---------------- DISCOVERY SCORING (safe placement) ----------------
    scores = []
    for _, rr in df_display.iterrows():
        s, label = score_row(rr.to_dict())
        scores.append({"Score": s, "Discovery Decision": label})

    df_scores = pd.DataFrame(scores)
    df_display = pd.concat([df_display.reset_index(drop=True), df_scores], axis=1)
    # -------------------------------------------------------------------

    df_display["Median Price"] = df_display["Median Price"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else ""
    )

    st.dataframe(
        df_display[
            ["State", "Suburb", "Median Price", "Days on Market", "Yield %", "Score", "Discovery Decision"]
        ],
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
                "Demand / Supply Ratio": analysis["Demand / Supply Ratio"],
                "Failed Gates": ", ".join(analysis["Failed Gates"]),
                "Narrative": analysis["Narrative"],
            })

 # ---------- RESULTS TABLES ----------
        st.subheader("✅ Deep Analysis Results")

        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(
            by=["Investability Score", "Demand / Supply Ratio"],
            ascending=[False, False]
        )

        # ---------- RISK APPETITE FILTERS (POST-ANALYSIS ONLY) ----------
        st.markdown("### ⚖️ Risk Appetite Filters (Post‑Analysis View)")
        st.caption(
            "These filters do NOT change BUY / AVOID decisions. "
            "They only control which analysed suburbs are shown based on your risk tolerance."
        )

        risk_renters_range = st.slider(
            "Renters proportion you are willing to consider (%)",
            min_value=10,
            max_value=60,
            value=(15, 35),
            step=1
        )

        risk_max_dom = st.slider(
            "Maximum Days on Market you are willing to consider",
            min_value=20,
            max_value=120,
            value=60,
            step=5
        )
        # --------------------------------------------------------------

        # View-only filtering (engine results remain untouched)
        df_view = df_results.copy()

        if "Renters %" in df_view.columns:
            df_view = df_view[
                (df_view["Renters %"] >= risk_renters_range[0]) &
                (df_view["Renters %"] <= risk_renters_range[1])
            ]

        if "Days on Market" in df_view.columns:
            df_view = df_view[df_view["Days on Market"] <= risk_max_dom]

        df_buy = df_view[df_view["Decision"] == "BUY"]
        df_avoid = df_view[df_view["Decision"] == "AVOID"]

        TOP_N = 5
        df_top_buy = df_buy.head(TOP_N)

        st.markdown("### 🏆 Top BUY Opportunities")
        st.dataframe(
            df_buy[
                [
                    "Suburb",
                    "Decision",
                    "Confidence",
                    "Confidence Score",
                    "Investability Score",
                    "Demand / Supply Ratio",
                    "Failed Gates"
                ]
            ],
            use_container_width=True
        )

        st.markdown("### ⚠️ AVOID / Watchlist Suburbs")
        st.dataframe(
            df_avoid[
                [
                    "Suburb",
                    "Decision",
                    "Confidence",
                    "Confidence Score",
                    "Investability Score",
                    "Demand / Supply Ratio",
                    "Failed Gates"
                ]
            ],
            use_container_width=True
        )

        # ---------- NARRATIVE ----------
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
