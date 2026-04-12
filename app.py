import streamlit as st
import pandas as pd

# ============================================================
# SAFE ENGINE IMPORT (Streamlit Cloud compatible)
# ============================================================
try:
    from engine import evaluate_suburb
except Exception:
    st.error("❌ Could not load engine.py. Ensure engine.py is in the app root.")
    st.stop()

# ============================================================
# APP SETUP
# ============================================================
st.set_page_config(page_title="Property Investment Accelerator Matcher", layout="wide")
st.title("🏠 Property Investment Accelerator Matcher")
st.subheader("Two‑Stage Discovery + Authoritative Logic Engine")

# ============================================================
# VIEW MODE
# ============================================================
view_mode = st.radio("View Mode", ("Client", "Advisor"), horizontal=True)

# ============================================================
# SESSION STATE
# ============================================================
for k, v in {
    "dsr_discovery_df": None,
    "explorer_discovery_df": None,
    "selected_suburbs": set(),
    "saved_shortlists": {},
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# CLIENT MODE
# ============================================================
client_mode = st.radio("Client Type", ("DSR Upload", "Explorer"), horizontal=True)

# ============================================================
# STAGE 1 — DISCOVERY (VISIBILITY ONLY)
# ============================================================
st.markdown("## 🟩 Stage 1 — Discovery Filters (Preferences Only)")

state = st.selectbox(
    "State", ["All", "NSW", "VIC", "QLD", "TAS", "NT", "WA", "SA"]
)
max_dom = st.slider("Maximum Days on Market", 0, 180, 90)
max_price = st.slider(
    "Maximum Median Price ($)",
    200_000, 2_000_000, 1_000_000,
    step=50_000,
)

def to_float(val):
    try:
        return float(val)
    except Exception:
        return None

# ============================================================
# DSR UPLOAD
# ============================================================
if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded_file and st.button("Apply Discovery Filters"):
        df = pd.read_excel(uploaded_file)

        df = df[
            ((df["State"] == state) | (state == "All")) &
            (df["Days on market"].apply(to_float) <= max_dom) &
            (df["Median 12 months"].apply(to_float) <= max_price)
        ]

        st.session_state.dsr_discovery_df = df

# ============================================================
# EXPLORER DEMO (Yield included for consistency)
# ============================================================
if client_mode == "Explorer" and st.button("Apply Discovery Filters"):
    st.session_state.explorer_discovery_df = pd.DataFrame([
        {
            "Suburb": "Grafton",
            "Yield %": 5.34,
            "_row": {
                "Days on market": 39,
                "Vacancy rate": 1.8,
                "Percent stock on market": 1.2,
                "Gross rental yield": 5.34,
                "Percent renters in market": 32,
                "Statistical reliability": 85
            }
        },
        {
            "Suburb": "Norville",
            "Yield %": 5.08,
            "_row": {
                "Days on market": 43,
                "Vacancy rate": 2.4,
                "Percent stock on market": 1.7,
                "Gross rental yield": 5.08,
                "Percent renters in market": 28,
                "Statistical reliability": 80
            }
        },
    ])

# ============================================================
# SELECT ACTIVE DATASET
# ============================================================
df = (
    st.session_state.dsr_discovery_df
    if client_mode == "DSR Upload"
    else st.session_state.explorer_discovery_df
)

# ============================================================
# STAGE 1 RESULTS
# ============================================================
if df is not None and not df.empty:
    st.markdown(f"## 📍 Discovery Results ({len(df)} suburbs)")

    display_cols = ["Suburb"]
    if "Yield %" in df.columns:
        display_cols.append("Yield %")

    st.dataframe(df[display_cols], use_container_width=True)

    suburbs = df.index.tolist()
    selected = st.multiselect(
        "Select suburbs for Deep Analysis",
        suburbs,
        default=list(st.session_state.selected_suburbs & set(suburbs)),
    )
    st.session_state.selected_suburbs = set(selected)

    # ========================================================
    # SHORTLIST LOADER
    # ========================================================
    if st.session_state.saved_shortlists:
        shortlist_name = st.selectbox(
            "Load shortlist",
            list(st.session_state.saved_shortlists.keys())
        )
        if st.button("Load Selected Shortlist"):
            shortlist_df = st.session_state.saved_shortlists[shortlist_name]
            st.session_state.selected_suburbs = set(
                df[df["Suburb"].isin(shortlist_df["Suburb"])].index
            )
            st.experimental_rerun()

    # ========================================================
    # STAGE 2 — DEEP ANALYSIS (ENGINE)
    # ========================================================
    if st.button("Run Deep Analysis"):
        results = []

        for i in selected:
            row = df.loc[i]
            analysis = evaluate_suburb(row["_row"])
            analysis["Suburb"] = row.get("Suburb", i)
            results.append(analysis)

        results_df = pd.DataFrame(results)

        # ====================================================
        # SORTING (Advisor only)
        # ====================================================
        if view_mode == "Advisor":
            sort_by = st.selectbox(
                "Sort results by",
                ("Confidence Score", "Demand Score")
            )
            results_df = results_df.sort_values(sort_by, ascending=False)

        # ====================================================
        # CONFIDENCE BADGES
        # ====================================================
        def confidence_badge(val):
            if val == "High":
                return "🟢 High"
            if val == "Medium":
                return "🟠 Medium"
            return "🔴 Low"

        results_df["Confidence"] = results_df["Confidence"].apply(confidence_badge)

        # ====================================================
        # DISPLAY COLUMNS
        # ====================================================
        display_cols = [
            "Suburb", "Decision", "Confidence",
            "Market Cycle", "Explanation"
        ]

        if view_mode == "Advisor":
            display_cols += [
                "Confidence Score",
                "Demand Score",
                "Failed Gates"
            ]

        st.dataframe(results_df[display_cols], use_container_width=True)

        # ====================================================
        # SAVE SHORTLIST
        # ====================================================
        shortlist_name = st.text_input("Save current shortlist as")
        if st.button("💾 Save Shortlist") and shortlist_name:
            st.session_state.saved_shortlists[shortlist_name] = results_df

        # ====================================================
        # MARKET CYCLE CHART (Advisor only)
        # ====================================================
        if view_mode == "Advisor":
            st.markdown("### Market Cycle Distribution")

            cycle_counts = results_df["Market Cycle"].value_counts()

            cycle_colors = {
                "Expansion": "#2E7D32",
                "Early Upswing": "#66BB6A",
                "Late Cycle / Peak": "#FFA726",
                "Stagnation": "#90A4AE",
                "Downturn": "#D32F2F",
            }

            colors = [cycle_colors.get(c, "#888888") for c in cycle_counts.index]

            try:
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots()
                cycle_counts.plot(kind="bar", color=colors, ax=ax)
                ax.set_ylabel("Suburbs")
                ax.set_xlabel("Market Cycle")
                st.pyplot(fig)
            except ModuleNotFoundError:
                st.bar_chart(cycle_counts)
                st.caption("📊 Streamlit chart used (matplotlib unavailable).")

            # Confidence legend
            st.markdown("**Confidence Legend:**")
            st.markdown("- 🟢 **High** — Strong alignment with investment criteria")
            st.markdown("- 🟠 **Medium** — Moderate risks or partial constraints")
            st.markdown("- 🔴 **Low** — Material risks or failing gates")

        # ====================================================
        # EXPORT
        # ====================================================
        st.download_button(
            "📥 Download Results (CSV)",
            results_df.to_csv(index=False).encode("utf-8"),
            "analysis_results.csv",
            "text/csv"
        )

st.caption("Property Investment Accelerator — Authoritative Logic Engine")
