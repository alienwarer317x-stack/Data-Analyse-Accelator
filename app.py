from ingestion.scoring import score_row
from engine import evaluate_suburb, evaluate_buy_gates, calculate_confidence
from ingestion.sqm_adapter import build_row_from_sqm
from ingestion.dsr_adapter import build_row_from_dsr
from ingestion.suburb_lookup import lookup_suburb
from ingestion.people_adapter import get_people_profile
from ingestion.fundamentals_adapter import get_structural_fundamentals
from ingestion.infrastructure_adapter import get_infrastructure_profile
from ingestion.property_evaluator import score_property_asset

import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")

st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two‑Stage Discovery + Authoritative Logic Engine")

# ====================== CONFIDENCE EXPLANATIONS ======================
CONFIDENCE_EXPLANATION = {
    "High": (
        "Strong alignment across demand, supply, rental returns, "
        "growth sustainability, and long‑term structural fundamentals."
    ),
    "Medium": (
        "Mixed signals present. Some strengths are offset by moderate "
        "risks or limitations in data confidence."
    ),
    "Low": (
        "Insufficient supporting evidence or multiple risk flags "
        "reduce overall conviction at this time."
    ),
}

# ====================== NARRATIVE FORMATTER (TABLE VIEW) ======================
def format_narrative_for_table(narrative):
    """
    Create a short, decision-appropriate summary
    for table display only.
    """
    if not isinstance(narrative, dict):
        return ""
    headline = narrative.get("headline", "")
    strengths = narrative.get("strengths") or []
    failed = narrative.get("failed_gate_explanations") or []
    risks = narrative.get("risks") or []
    # BUY: highlight strongest positive
    if "BUY" in headline.upper():
        if strengths:
            return f"{headline} — {strengths[0]}"
        return headline
    # AVOID: highlight primary failure or risk
    if "AVOID" in headline.upper():
        if failed:
            return f"{headline} — {failed[0]}"
        if risks:
            return f"{headline} — {risks[0]}"
        return headline
    return headline


# ====================== SESSION STATE ======================
if "dsr_discovery_df" not in st.session_state:
    st.session_state.dsr_discovery_df = None
if "explorer_discovery_df" not in st.session_state:
    st.session_state.explorer_discovery_df = None
if "dsr_selected_suburbs" not in st.session_state:
    st.session_state.dsr_selected_suburbs = set()
if "explorer_selected_suburbs" not in st.session_state:
    st.session_state.explorer_selected_suburbs = set()
if "risk_renters_range" not in st.session_state:
    st.session_state.risk_renters_range = (15, 35)
if "risk_max_dom" not in st.session_state:
    st.session_state.risk_max_dom = 60
if "deep_analysis_results" not in st.session_state:
    st.session_state.deep_analysis_results = None


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
           
            if price is not None and price > max_price:
                continue
            discovered.append({
                "State": r.get("State"),
                "Suburb": r.get("Suburb"),
                "Median Price": price,
                "Days on Market": dom,
                "Post code": r.get("Post code") or r.get("Post Code"),
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
    df = df[df["Median Price"] <= max_price]
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
           
            narr = analysis.get("Narrative", {})
            growth_info = analysis.get("Growth", {})
            results.append({
                "Suburb": r["Suburb"],
                "State": r.get("State"),
                "Post code": r.get("Post code"),
                "Decision": analysis["Decision"],
                "Confidence": analysis["Confidence"],
                "Confidence Score": analysis["Confidence Score"],
                "Investability Score": analysis["Investability Score"],
                "Demand / Supply Ratio": analysis["Demand / Supply Ratio"],
               
            # ✅ NEW — Growth visibility
                "AVG GR 3yrs (%)": growth_info.get("avg_36m"),
                "10y Growth Rate % OTH": growth_info.get("oth_cagr"),
                "Total CAGR 10yrs (%)": growth_info.get("total_cagr"),
                "Failed Gates": ", ".join(analysis.get("Failed Gates", [])),
                "Narrative": narr,
            })
        # ✅ STORE RESULTS — ENGINE RUNS ONCE
        st.session_state.deep_analysis_results = results


# ====================== STAGE 2 — RESULTS VIEW ======================
if st.session_state.deep_analysis_results:
    st.subheader("✅ Deep Analysis Results")
    df_results = pd.DataFrame(st.session_state.deep_analysis_results)
   
    # Clean narrative for table display
    if "Narrative" in df_results.columns:
        df_results["Narrative"] = df_results["Narrative"].apply(
            format_narrative_for_table)
   
    df_results = df_results.sort_values(
        by=["Investability Score", "Demand / Supply Ratio"],
        ascending=[False, False]
    )
        # ---------- RISK APPETITE FILTERS ----------
    st.markdown("### ⚖️ Risk Appetite Filters (Post‑Analysis View)")
    st.caption(
        "These filters do NOT change BUY / AVOID decisions. "
        "They only adjust which analysed suburbs are shown."
    )

    # Existing filters
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        risk_renters_range = st.slider(
            "Renters proportion you are willing to consider (%)",
            min_value=10,
            max_value=60,
            value=st.session_state.risk_renters_range,
            step=1,
            key="risk_renters_range"
        )
    with col_r2:
        risk_max_dom = st.slider(
            "Maximum Days on Market you are willing to consider",
            min_value=0,
            max_value=120,
            value=st.session_state.risk_max_dom,
            step=5,
            key="risk_max_dom"
        )

    # === NEW FILTERS ===
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        risk_vacancy = st.slider(
            "Maximum Vacancy Rate (%) you are willing to consider",
            min_value=0.0,
            max_value=5.0,
            value=2.0,
            step=0.1,
            key="risk_vacancy"
        )

        risk_stock_on_market = st.slider(
            "Maximum Stock on Market (%) you are willing to consider",
            min_value=0.0,
            max_value=3.0,
            value=1.3,
            step=0.1,
            key="risk_stock_on_market"
        )

    with col_f2:
        risk_yield = st.slider(
            "Minimum Gross Rental Yield (%) you are willing to consider",
            min_value=2.0,
            max_value=10.0,
            value=4.0,
            step=0.1,
            key="risk_yield"
        )

        # Avg Vendor Discounting % (assuming column name is "Avg vendor discounting" or similar)
        risk_discount = st.slider(
            "Maximum Avg Vendor Discounting (%) you are willing to consider",
            min_value=0.0,
            max_value=15.0,
            value=8.0,
            step=0.5,
            key="risk_discount"
        )
      # ========== APPLY ALL RISK APPETITE FILTERS ==========
    df_view = df_results.copy()

    # 1. Renters % filter
    if "Renters %" in df_view.columns:
        df_view = df_view[
            (df_view["Renters %"] >= risk_renters_range[0]) &
            (df_view["Renters %"] <= risk_renters_range[1])
        ]

    # 2. Maximum Days on Market
    if "Days on Market" in df_view.columns:
        df_view = df_view[df_view["Days on Market"] <= risk_max_dom]

    # 3. Vacancy Rate
    if "Vacancy rate" in df_view.columns or "Vacancy rate%" in df_view.columns:
        vacancy_col = "Vacancy rate" if "Vacancy rate" in df_view.columns else "Vacancy rate%"
        df_view = df_view[df_view[vacancy_col] <= risk_vacancy]

    # 4. Stock on Market
    if "Stock on market" in df_view.columns or "Stock on market%" in df_view.columns or "Percent stock on market" in df_view.columns:
        stock_col = next((col for col in ["Stock on market", "Stock on market%", "Percent stock on market"] if col in df_view.columns), None)
        if stock_col:
            df_view = df_view[df_view[stock_col] <= risk_stock_on_market]

    # 5. Gross Rental Yield (Minimum)
    if "Gross rental yield" in df_view.columns or "Gross rental yield%" in df_view.columns or "Yield %" in df_view.columns:
        yield_col = next((col for col in ["Gross rental yield", "Gross rental yield%", "Yield %"] if col in df_view.columns), None)
        if yield_col:
            df_view = df_view[df_view[yield_col] >= risk_yield]

    # 6. Avg Vendor Discounting (Maximum)
    if "Avg vendor discounting" in df_view.columns or "Avg vendor discounting%" in df_view.columns or "Vendor discounting" in df_view.columns:
        discount_col = next((col for col in ["Avg vendor discounting", "Avg vendor discounting%", "Vendor discounting"] if col in df_view.columns), None)
        if discount_col:
            df_view = df_view[df_view[discount_col] <= risk_discount]

    # ========== DECISION LENS ==========
    st.markdown("### ⚖️ Decision Lens")
    view_mode = st.radio(
        "View mode",
        options=["Strict (Engine BUY only)", "Expanded (Risk-tolerant view)"],
        horizontal=True
    )

    # Apply View Mode Logic
    if view_mode == "Strict (Engine BUY only)":
        df_display = df_view[df_view["Decision"] == "BUY"]          # Strict = Only BUYs
    else:
        df_display = df_view.copy()                                  # Expanded = Show all that passed risk filters

    # Display Tables
    st.markdown("### 🏆 Top BUY Opportunities")
    cols = [
        "Suburb", "State", "Post code", "Decision", "Confidence",
        "Investability Score", "Demand / Supply Ratio",
        "AVG GR 3yrs (%)", "10y Growth Rate % OTH", "Total CAGR 10yrs (%)", "Failed Gates"
    ]
    available_cols = [c for c in cols if c in df_display.columns]
    st.dataframe(df_display[available_cols], use_container_width=True)

    st.markdown("### ⚠️ AVOID / Watchlist Suburbs")
    avoid_df = df_display[df_display["Decision"] != "BUY"]
    st.dataframe(avoid_df[available_cols], use_container_width=True)

    # ====================== SUBURB PROFILE (SELECT ONE) ======================
    st.subheader("🏘️ Suburb Profile")

    # Use the currently displayed dataframe for profile selection
    if not df_display.empty:
        profile_options = df_display["Suburb"].tolist()
        if view_mode == "Strict (Engine BUY only)":
            st.caption("Showing suburbs from 🏆 Top BUY Opportunities.")
        else:
            st.caption("Showing suburbs based on your Risk Appetite filters (Expanded view).")
    else:
        profile_options = []
        st.caption("No suburbs match your current filters.")

    selected_profile_suburb = st.selectbox(
        "Select a suburb to view details",
        options=profile_options,
        key="selected_profile_suburb"
    )

    # Build a quick lookup from stored deep analysis results
    results_list = st.session_state.get("deep_analysis_results")
    if not isinstance(results_list, list) or not results_list:
        st.info("Run Deep Analysis to view suburb details.")
        st.stop()

    res_map = {r["Suburb"]: r for r in results_list}
    chosen = res_map.get(selected_profile_suburb)

    # Pull extra suburb facts from the current discovery dataframe
    extra = None
    try:
        match = current_discovery_df[current_discovery_df["Suburb"] == selected_profile_suburb]
        if not match.empty:
            extra = match.iloc[0].to_dict()
    except Exception:
        extra = None

    # Enrich suburb data using lookup table
    lookup = lookup_suburb(
        selected_profile_suburb,
        extra.get("State") if extra else None
    )
    postcode = lookup.get("Postcode")

    # ====================== SUBURB PROFILE ======================
    if chosen:
        st.markdown(f"### {chosen['Suburb']}")
        # ====================== A) SUBURB PROFILE TABS ======================
        tabs = st.tabs(["Overview", "People", "Economy", "Infrastructure", "Risk"])
       
        # ====================== A1 / A2 — OVERVIEW ======================
        with tabs[0]:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Decision", chosen["Decision"])
            c2.metric("Confidence",chosen.get("Confidence"),help=CONFIDENCE_EXPLANATION.get(chosen.get("Confidence"), ""))
            c3.metric("Investability Score", chosen["Investability Score"])
            c4.metric("Demand / Supply Ratio", chosen["Demand / Supply Ratio"])
            st.markdown("#### 📈 Growth Summary")
           
            g1, g2, g3 = st.columns(3)
           
            g1.metric(
                "AVG GR 3yrs (%)",
                f"{chosen.get('AVG GR 3yrs (%)', '—')}"
            )
           
            g2.metric(
                "10y Growth Rate % (OTH)",
                f"{chosen.get('10y Growth Rate % OTH', '—')}"
            )
           
            g3.metric(
                "Total CAGR 10yrs (%)",
                f"{chosen.get('Total CAGR 10yrs (%)', '—')}"
            )
            # ⚠️ Growth alignment warning (HOLD / Review explanation)
            if "Alignment Issue" in str(chosen.get("Failed Gates", "")):
                st.warning(
                    "📊 **Growth data alignment note:**\n\n"
                    "Long‑term growth is within acceptable limits, however estimates from "
                    "different data sources diverge by more than expected. "
                    "This suburb has been flagged for **manual review** to confirm data accuracy "
                    "before proceeding."
                )
           
            # Extra facts (from discovery data)
            if extra:
                st.markdown("#### 📌 Quick Facts (from discovery data)")
                f0, f1, f2, f3, f4 = st.columns(5)
                f0.metric("Post code", extra.get("Post code", ""))
                f1.metric("State", extra.get("State", ""))
                f2.metric("Days on Market", extra.get("Days on Market", ""))
                f3.metric("Yield %", extra.get("Yield %", ""))
                f4.metric("Median Price", extra.get("Median Price", ""))
            # ====================== C / C1 — MAP ======================
            st.markdown("#### 🗺️ Map")
            map_query = f"{chosen['Suburb']}, {extra.get('State', '')} {extra.get('Postcode', '')}".replace(" ", "+")
            st.components.v1.iframe(
                src=f"https://www.google.com/maps?q={map_query}&output=embed",
                height=800
            )
            # Quick links
            st.link_button(
                "🗺️ Open in Google Maps",
                f"https://www.google.com/maps/search/?api=1&query={chosen['Suburb']} {extra.get('State', '')}"
            )
            st.link_button(
                "🔎 Search AreaSearch for this suburb",
                f"https://www.google.com/search?q=site:areasearch.com.au+suburb+{chosen['Suburb']}"
            )
            st.markdown("### 📋 Investment Summary")
           
            summary_rows = [
                ["Decision", chosen.get("Decision")],
                ["Confidence", chosen.get("Confidence")],
                ["Confidence Score", chosen.get("Confidence Score")],
                ["Failed Gates", chosen.get("Failed Gates") or "None"],
            ]
           
            narrative = chosen.get("Narrative", {})
            strengths = narrative.get("strengths") or []
            risks = narrative.get("risks") or []
           
            summary_rows.append(
                ["Key Strength", strengths[0] if strengths else "—"]
            )
            summary_rows.append(
                ["Key Risk", risks[0] if risks else "No material risks identified"]
            )
           
            df_summary = pd.DataFrame(summary_rows, columns=["Item", "Summary"])
           
            st.table(df_summary)
           
          
            # Narrative summary
            narrative = chosen.get("Narrative", {})
           
            # Optional: path-to-buy
            path = narrative.get("path_to_buy", [])
            if path:
                st.markdown("#### 🔁 What would need to change to become a BUY")
                for p in path[:6]:
                    st.markdown(f"- {p}")
            # ====================== 🧾 Sources & Confidence ======================
            st.markdown("**Data Sources Used**")
            st.markdown("- ABS Census (Population & Demographics)")
            st.markdown("- SQM Research (Market metrics)")
            st.markdown("- HTAG / OnTheHouse (Growth indicators)")
            st.markdown("- Internal structural assessment (Employment, supply, affordability)")
            st.caption(
                "All investment decisions are generated by an authoritative rules engine. "
                "Displayed data is factual and does not override BUY / AVOID logic."
            )
            with st.expander("How confidence is calculated"):
                st.write(
                    "Confidence reflects the degree of alignment across multiple factors, "
                    "including market demand, supply conditions, rental returns, "
                    "growth sustainability, and long‑term structural fundamentals. "
                    "It does not represent certainty, but rather the strength of evidence "
                    "supporting the investment decision."
                    )

        # ====================== B / B1 — PEOPLE ======================
        with tabs[1]:
            st.markdown("#### 👥 Population & Demographics")
            people = get_people_profile(
                suburb=chosen["Suburb"],
                state=extra.get("State"),
                postcode=chosen.get("Postcode")
            )
            if not people:
                st.info("ABS / Census data not available for this suburb yet.")
            else:
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("Population", people.get("population"))
                p2.metric("Population Growth (%)", people.get("population_growth_pct"))
                p3.metric("Median Age", people.get("median_age"))
                p4.metric("Household Size", people.get("household_size"))
                st.markdown("**Household Composition**")
                st.write(f"- Families: {people.get('families_pct')}%")
                st.write(f"- Renters: {people.get('renters_pct')}%")
                st.write(f"- Owner-occupiers: {people.get('owners_pct')}%")

        # ====================== OPTIONAL — ECONOMY ======================
        with tabs[2]:
            st.markdown("#### 🏭 Economy & Employment")
            structural = get_structural_fundamentals(chosen["Suburb"])
            if not structural:
                st.info("Economic and employment data not available for this suburb yet.")
            else:
                st.markdown("**Employment Structure**")
                if structural.get("industry_diversification") is True:
                    st.success("Employment base is diversified")
                elif structural.get("industry_diversification") is False:
                    st.warning("Employment base is concentrated")
                else:
                    st.info("Employment diversification data unavailable")
                jobs = structural.get("job_infrastructure_count")
                if jobs is not None:
                    st.metric("Major employment nodes", jobs)
                st.markdown("**Income & Affordability Signals**")
                if structural.get("income_growth_2016") is True or structural.get("income_growth_2021") is True:
                    st.success("Household incomes have improved over time")
                elif structural.get("income_growth_2016") is False and structural.get("income_growth_2021") is False:
                    st.warning("Household income growth has been weak")
                else:
                    st.info("Income growth data unavailable")
               
                affordability = structural.get("housing_affordability")
                if affordability == "Good":
                    st.success("Housing affordability remains supportive")
                elif affordability == "Poor":
                    st.warning("Housing affordability is stretched")

        # ====================== OPTIONAL — INFRASTRUCTURE ======================
        with tabs[3]:
            st.markdown("#### 🚧 Infrastructure & Amenities")
            structural = get_structural_fundamentals(chosen["Suburb"])
            if not structural:
                st.info("Infrastructure data not available for this suburb yet.")
            else:
                travel = structural.get("average_travel_time")
            if travel is not None:
                st.metric("Average Commute Time (mins)", travel)
                if travel <= 35:
                    st.success("Commute times are favourable")
                elif travel <= 50:
                    st.info("Commute times are moderate")
                else:
                    st.warning("Commute times are long")
            else:
                st.info("Commute time data unavailable")

        # ---------- Physical Infrastructure (Schools & Healthcare) ----------
        lat = lookup.get("Latitude")
        lon = lookup.get("Longitude")
        infra = get_infrastructure_profile(lat, lon)
        st.markdown("**Schools (within 10 km)**")
        if infra["schools"]:
            for s in infra["schools"]:
                st.markdown(f"- {s['name']} ({s['type']}) — {s['distance_km']} km")
        else:
            st.info("No schools found within 10 km.")
        st.markdown("**Hospitals & Medical Centres (within 10 km)**")
        if infra["hospitals"]:
            for h in infra["hospitals"]:
                st.markdown(f"- {h['name']} — {h['distance_km']} km")
        else:
            st.info("No hospitals found within 10 km.")

        # ====================== OPTIONAL — RISK ======================
        with tabs[4]:
            st.markdown("#### ⚠️ Investment Risk Summary")
            st.write("**Failed Gates:**")
            st.write(chosen.get("Failed Gates", "None"))
            narrative = chosen.get("Narrative", {})
            risks = narrative.get("risks", [])
            if risks:
                for r in risks:
                    st.markdown(f"- {r}")
            else:
                st.write("No major risks identified.")


# ====================== STAGE 3 — ASSET SELECTION ======================
if chosen == None:
    st.write("Please select a suburb to begin.")
    # Everything below this line must be indented (shifted right) to stay inside the 'if'
    st.divider()
    st.markdown("## 🔍 Stage 3 — Individual Property Analysis")
    st.subheader(f"Evaluate an Asset in {chosen['Suburb']}")
    st.info("Agent Tip: A great suburb can still have bad houses. Use this checklist to ensure the specific property is an 'A-Grade' asset.")

    with st.expander("📝 Physical Property Checklist", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            land = st.number_input("Land Size (sqm)", value=450, step=10)
            frontage = st.number_input("Frontage (m)", value=12.0, step=0.5)
            orientation = st.checkbox("North-Facing Backyard?", help="Optimal for natural light and capital growth.")
        with col2:
            main_road = st.checkbox("Is it on a Main Road?", help="Properties on main roads often suffer from higher days-on-market and lower growth.")
            renovated = st.selectbox("Internal Condition", ["Original", "Neat", "Renovated", "New / Brand New"])

        if st.button("Generate Asset Verdict"):
            # Call the logic from property_evaluator.py
            asset_result = score_property_asset({
                "land_size": land,
                "frontage_metres": frontage,
                "north_facing_rear": orientation,
                "on_main_road": main_road
            })
            
            st.divider()
            
            # Display Grade and Score
            val_col1, val_col2 = st.columns(2)
            val_col1.metric("Asset Grade", asset_result["grade"])
            val_col2.metric("Asset Score", f"{asset_result['asset_score']}/100")

            # Final Advice Narrative
            if asset_result["asset_score"] >= 80:
                st.success(f"**Verdict:** This is a premium asset for {chosen['Suburb']}. Proceed to Stage 4: Due Diligence.")
            elif asset_result["asset_score"] >= 65:
                st.warning(f"**Verdict:** This is a secondary (B-Grade) asset. Ensure you are not overpaying.")
            else:
                st.error(f"**Verdict:** Avoid. This asset has structural compromises that will hinder long-term performance.")

            # Pros and Cons
            c_pos, c_neg = st.columns(2)
            with c_pos:
                st.write("**Investment Boosters**")
                for p in asset_result["positives"]: st.write(f"✅ {p}")
            with c_neg:
                st.write("**Risk Factors**")
                for n in asset_result["negatives"]: st.write(f"❌ {n}")

# ====================== STAGE 4 — ROADMAP ======================
if chosen:
     st.markdown("## 🛠️ Stage 4 — Next Steps")
     st.write("Ready to proceed? [Download Buyer's Agent Checklist PDF]")
