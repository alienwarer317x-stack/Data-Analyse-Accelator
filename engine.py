# ============================================================
# PROPERTY INVESTMENT ACCELERATOR — LOGIC ENGINE
# ============================================================

# ---------------- NORMALISATION ----------------

def normalise_percent(val):
    if val is None:
        return None
    try:
        v = float(str(val).replace("%", "").strip())
        return v * 100 if v <= 1 else v
    except:
        return None


def normalise_plain(val):
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None


def clamp(value, lo=0.0, hi=1.0):
    if value is None:
        return None
    return max(lo, min(value, hi))


# ---------------- DEMAND → SUPPLY ----------------

def calculate_demand_supply_ratio(
    vacancy_rate,
    stock_on_market,
    days_on_market,
    vacancy_upper_bound=5.0,
    stock_upper_bound=2.5,
    dom_long_term_avg=60.0,
):
    if vacancy_rate is None or stock_on_market is None or days_on_market is None:
        return None

    vacancy_component = clamp(1 - vacancy_rate / vacancy_upper_bound)
    stock_component = clamp(1 - stock_on_market / stock_upper_bound)
    dom_component = clamp(1 - days_on_market / dom_long_term_avg)

    if None in (vacancy_component, stock_component, dom_component):
        return None

    score = (
        0.40 * vacancy_component +
        0.35 * stock_component +
        0.25 * dom_component
    )

    return round(score * 100, 1)


# ---------------- BUY GATES ----------------

def evaluate_buy_gates(factors):
    failed = []

    if factors["renters_pct"] is None or not (15 <= factors["renters_pct"] <= 35):
        failed.append("Renters %")

    if factors["vacancy_pct"] is None or factors["vacancy_pct"] >= 2:
        failed.append("Vacancy")

    if factors["demand_supply_ratio"] is None or factors["demand_supply_ratio"] <= 55:
        failed.append("Demand / Supply")

    if factors["stock_on_market_pct"] is None or factors["stock_on_market_pct"] >= 1.3:
        failed.append("Stock on Market")

    if factors["gross_rental_yield"] is None or factors["gross_rental_yield"] <= 4:
        failed.append("Gross Yield")

    if factors["statistical_reliability"] is not None and factors["statistical_reliability"] <= 51:
        failed.append("Reliability")

    return ("BUY" if not failed else "AVOID"), failed


# ---------------- GROWTH ----------------

def calculate_cagr(total_growth_pct, years):
    if total_growth_pct is None or years <= 0:
        return None
    return ((1 + total_growth_pct / 100) ** (1 / years) - 1) * 100


def consolidate_growth_metrics(row):
    values = [row.get(k) for k in ("sqm_10y_growth_pct", "oth_10y_growth_pct", "htag_10y_growth_pct")]
    vals = [v for v in values if isinstance(v, (int, float))]
    avg = sum(vals) / len(vals) if vals else None
    return {
        "sqm_36m_growth_pct": row.get("sqm_36m_growth_pct"),
        "avg_10y_growth_pct": avg,
        "cagr_10y_pct": calculate_cagr(avg, 10) if avg else None,
    }


def evaluate_growth_gates(growth):
    failed = []
    if growth["sqm_36m_growth_pct"] and growth["sqm_36m_growth_pct"] > 50:
        failed.append("36m Growth Too High")
    if growth["cagr_10y_pct"] and growth["cagr_10y_pct"] > 7:
        failed.append("10yr CAGR Too High")
    return failed


# ---------------- CONFIDENCE ----------------

def calculate_confidence(decision):
    score = 85 if decision == "BUY" else 60
    return score, ("High" if score >= 75 else "Medium")


def classify_market_cycle(dsr):
    if dsr is None:
        return "Unknown"
    if dsr >= 70:
        return "Expansion"
    if dsr >= 60:
        return "Upswing"
    if dsr >= 50:
        return "Stagnation"
    return "Downturn"


# ---------------- SUBURB EVALUATION ----------------

def evaluate_suburb(row):
    # ✅ LAZY IMPORT — fixes Streamlit ImportError
    from ingestion.fundamentals_adapter import (
        get_structural_fundamentals,
        evaluate_structural_gates,
    )

    vacancy = normalise_plain(row.get("Vacancy rate"))
    stock = normalise_plain(row.get("Percent stock on market"))
    dom = normalise_plain(row.get("Days on market"))
    yield_pct = normalise_percent(row.get("Gross rental yield"))
    renters_pct = normalise_percent(row.get("Percent renters in market"))
    reliability = normalise_plain(row.get("Statistical reliability"))

    demand_supply = calculate_demand_supply_ratio(vacancy, stock, dom)

    decision, failed = evaluate_buy_gates({
        "renters_pct": renters_pct,
        "vacancy_pct": vacancy,
        "demand_supply_ratio": demand_supply,
        "stock_on_market_pct": stock,
        "gross_rental_yield": yield_pct,
        "statistical_reliability": reliability,
    })

    growth = consolidate_growth_metrics(row)
    failed += evaluate_growth_gates(growth)

    if failed:
        decision = "AVOID"

    structural = get_structural_fundamentals(row)
    structural_eval = evaluate_structural_gates(structural)

    confidence_score, confidence_band = calculate_confidence(decision)

    return {
        "Decision": decision,
        "Confidence": confidence_band,
        "Confidence Score": confidence_score,
        "Demand / Supply Ratio": demand_supply,
        "Market Cycle": classify_market_cycle(demand_supply),
        "Failed Gates": failed or ["None"],
        "Growth": growth,
        "Structural Fundamentals": structural,
        "Structural Evaluation": structural_eval,
    }
