import streamlit as st
import pandas as pd
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
st.caption("Visibility filters only. No investment logic or BUY gates.")

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
        step=50_000,
    )
    min_yield = st.slider(
        "Minimum Gross Rental Yield (%)",
        3.0, 8.0, 4.0,
    )

# ====================== RESET ======================
if st.button("Reset"):
    st.session_state.dsr_discovery_df = None
    st.session_state.explorer_discovery_df = None
    st.session_state.dsr_selected_suburbs = set()
    st.session_state.explorer_selected_suburbs = set()

# ====================== NORMALISATION HELPERS ======================
def normalise_plain(val):
    try:
        return float(str(val).replace("%", "").replace("days", "").strip())
    except:
        return None

def normalise_percent(val):
    try:
        v = float(str(val).replace("%", "").strip())
        return v * 100 if v <= 1 else v
    except:
        return None

# ====================== STAGE 2 DERIVED METRICS ======================
def calculate_demand_supply_ratio(vacancy_pct, stock_pct, dom_days, dom_avg=60):
    if None in (vacancy_pct, stock_pct, dom_days):
        return None

    vacancy_score = max(0, min(1, 1 - vacancy_pct / 5.0))
    stock_score = max(0, min(1, 1 - stock_pct / 2.5))
    dom_score = max(0, min(1, 1 - dom_days / dom_avg))

    raw = 0.40 * vacancy_score + 0.35 * stock_score + 0.25 * dom_score
    return round(raw * 100, 1)

def classify_market_cycle(score, vacancy_pct=5, stock_pct=3):
    if score >= 70 and stock_pct < 1.0:
        return "Expansion"
    if score >= 60 and vacancy_pct < 2.0:
        return "Early Upswing"
    if score >= 60 and stock_pct >= 1.5:
        return "Late Cycle / Peak"
    if score < 45 and stock_pct > 2.0:
        return "Downturn"
    return "Stagnation"

def generate_narrative(decision, demand_score, vacancy, stock, dom, yld, band, failed):
    v = f"{vacancy:.1f}%" if vacancy is not None else "?"
    s = f"{stock:.1f}%" if stock is not None else "?"
    d = f"{dom:.0f} days" if dom is not None else "?"
    y = f"{yld:.1f}%" if yld is not None else "?"

    if decision == "BUY":
        return (
            f"Strong demand relative to supply (score {demand_score}). "
            f"Vacancy {v}, stock on market {s}, days on market {d}. "
            f"Gross rental yield {y}. Confidence: {band}."
        )

    failed_txt = ", ".join(failed) if failed else "multiple gates"
    return (
        f"Weak demand (score {demand_score}). "
        f"Failed gates: {failed_txt}. "
        f"Vacancy {v}, stock {s}, days on market {d}, yield {y}. "
        f"Confidence: {band}."
    )

# ====================== DSR UPLOAD MODE ======================
if client_mode == "DSR Upload":
    uploaded_file = st.file_uploader("Upload your DSR Excel file", type=["xlsx"])

    if uploaded_file and st.button("Apply Discovery Filters"):
        df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
        discovered = []

        for _, r in df.iterrows():
            if selected_state != "All" and r.get("State") != selected_state:
                continue

            dom = normalise_plain(r.get("Days on market"))
            price = normalise_plain(r.get("Typical value")) or normalise_plain(r.get("Median 12 months"))
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
                "_row": r
            })

        st.session_state.dsr_discovery_df = pd.DataFrame(discovered)

# ====================== EXPLORER MODE ======================
if client_mode == "Explorer" and st.button("Apply Discovery Filters"):
    demo_data = [
        {
            "State": "NSW",
            "Suburb": "Grafton",
            "Median Price": 520000,
            "Days on Market": 39,
            "Yield %": 5.34,
            "_row": {
                "Vacancy rate": 1.8,
                "Percent stock on market": 1.2,
                "Gross rental yield": 5.34,
                "Percent renters in market": 32,
                "Statistical reliability": 85,
                "Days on market": 39
            }
        },
        {
            "State": "QLD",
            "Suburb": "Norville",
            "Median Price": 570000,
            "Days on Market": 43,
            "Yield %": 5.08,
            "_row": {
                "Vacancy rate": 2.4,
                "Percent stock on market": 1.7,
                "Gross rental yield": 5.08,
                "Percent renters in market": 28,
                "Statistical reliability": 80,
                "Days on market": 43
            }
        }
    ]

    df = pd.DataFrame(demo_data)
    df = df[
        (df["Days on Market"] <= max_dom) &
        (df["Median Price"] <= max_price)
    ]
    st.session_state.explorer_discovery_df = df

# ====================== STAGE 1 RESULTS ======================
current_df = None
current_selected = set()

if client_mode == "DSR Upload" and st.session_state.dsr_discovery_df is not None:
    current_df = st.session_state.dsr_discovery_df
    current_selected = st.session_state.dsr_selected_suburbs
elif client_mode == "Explorer" and st.session_state.explorer_discovery_df is not None:
    current_df = st.session_state.explorer_discovery_df
    current_selected = st.session_state.explorer_selected_suburbs

if current_df is not None and not current_df.empty:
    st.markdown("## 📍 Discovery Results")

    df_display = current_df.copy()
    df_display["Median Price"] = df_display["Median Price"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else ""
    )

    st.dataframe(
        df_display[["State", "Suburb", "Median Price", "Days on Market", "Yield %"]],
        use_container_width=True
    )

    selected = st.multiselect(
        "Select suburbs for Deep Analysis",
        options=current_df["Suburb"].tolist(),
        default=current_df["Suburb"].tolist()
    )

    if client_mode == "DSR Upload":
        st.session_state.dsr_selected_suburbs = set(selected)
        current_selected = st.session_state.dsr_selected_suburbs
    else:
        st.session_state.explorer_selected_suburbs = set(selected)
        current_selected = st.session_state.explorer_selected_suburbs

# ====================== STAGE 2 — DEEP ANALYSIS ======================
if current_selected:
    st.markdown("## 🟥 Stage 2 — Deep Analysis (Authoritative Engine)")

    if st.button("Run Deep Analysis on Selected Suburbs"):
        results = []

        for _, r in current_df.iterrows():
            if r["Suburb"] not in current_selected:
                continue

            row = r["_row"]

            vacancy = normalise_plain(row.get("Vacancy rate"))
            stock = normalise_plain(row.get("Percent stock on market"))
            dom = normalise_plain(row.get("Days on market"))
            yld = normalise_percent(row.get("Gross rental yield"))

            demand_score = calculate_demand_supply_ratio(vacancy, stock, dom)

            factors = {
                "renters_pct": normalise_percent(row.get("Percent renters in market")),
                "vacancy_pct": vacancy,
                "demand_supply_ratio": demand_score,  # ✅ FIXED
                "stock_on_market_pct": stock,
                "gross_rental_yield": yld,
                "statistical_reliability": normalise_plain(row.get("Statistical reliability")),
            }

            decision, failed = evaluate_buy_gates(factors)
            score, band = calculate_confidence(decision)

            cycle = classify_market_cycle(demand_score or 0, vacancy or 5, stock or 3)
            narrative = generate_narrative(decision, demand_score, vacancy, stock, dom, yld, band, failed)

            results.append({
                "Suburb": r["Suburb"],
                "Decision": decision,
                "Confidence": band,
                "Confidence Score": score,
                "Market Cycle": cycle,
                "Explanation": narrative,
                "Failed Gates": ", ".join(failed) if failed else "None"
            })

        st.dataframe(pd.DataFrame(results), use_container_width=True)

st.caption("Property Investment Accelerator — Authoritative Logic Engine")
