# engine.py
# ============================================================
# PROPERTY INVESTMENT ACCELERATOR — LOGIC ENGINE
# ============================================================

def normalise_percent(val):
    """
    Handles:
    0.24  -> 24
    24    -> 24
    '24%' -> 24
    """
    if val is None:
        return None
    try:
        val = float(str(val).replace("%", "").strip())
        return val * 100 if val <= 1 else val
    except:
        return None


def normalise_plain(val):
    """
    Handles index / real percentage scales
    (vacancy %, stock %, reliability, etc.)
    """
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None


def clamp(value, lower=0.0, upper=1.0):
    return max(lower, min(value, upper))


# ------------------------------------------------------------
# Demand / Supply (DERIVED — NOT SCRAPED)
# ------------------------------------------------------------
def calculate_demand_supply_ratio(
    vacancy_pct,
    stock_on_market_pct,
    days_on_market,
    dom_long_term_avg=60,
    vacancy_upper_bound=5.0,
    stock_upper_bound=2.5
):
    if (
        vacancy_pct is None or
        stock_on_market_pct is None or
        days_on_market is None or
        dom_long_term_avg <= 0
    ):
        return None

    vacancy_score = clamp(1 - vacancy_pct / vacancy_upper_bound)
    stock_score = clamp(1 - stock_on_market_pct / stock_upper_bound)
    dom_score = clamp(1 - days_on_market / dom_long_term_avg)

    raw = (
        0.40 * vacancy_score +
        0.35 * stock_score +
        0.25 * dom_score
    )

    return round(raw * 100, 1)


# ------------------------------------------------------------
# BUY / AVOID GATES
# ------------------------------------------------------------
def evaluate_buy_gates(factors):
    failed = []

    if factors.get("renters_pct") is None or not (15 <= factors["renters_pct"] <= 35):
        failed.append("Renters %")

    if factors.get("vacancy_pct") is None or factors["vacancy_pct"] >= 2:
        failed.append("Vacancy")

    if factors.get("demand_supply_ratio") is None or factors["demand_supply_ratio"] <= 55:
        failed.append("Demand / Supply")

    if factors.get("stock_on_market_pct") is None or factors["stock_on_market_pct"] >= 1.3:
        failed.append("Stock on Market")

    if factors.get("gross_rental_yield") is None or factors["gross_rental_yield"] <= 4:
        failed.append("Gross Yield")

    if factors.get("statistical_reliability") is None or factors["statistical_reliability"] <= 51:
        failed.append("Reliability")

    decision = "BUY" if not failed else "AVOID"
    return decision, failed


# ------------------------------------------------------------
# CONFIDENCE
# ------------------------------------------------------------
def calculate_confidence(decision):
    score = 85 if decision == "BUY" else 60
    band = "High" if score >= 75 else "Medium"
    return score, band


# ------------------------------------------------------------
# MARKET CYCLE (OPTIONAL BUT USED BY APP)
# ------------------------------------------------------------
def classify_market_cycle(score):
    if score is None:
        return "Unknown"
    if score >= 70:
        return "Expansion"
    if score >= 60:
        return "Upswing"
    if score >= 50:
        return "Stagnation"
    return "Downturn"


# ------------------------------------------------------------
# ✅ SINGLE AUTHORITATIVE ENTRY POINT
# ------------------------------------------------------------
def evaluate_suburb(row):
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

    confidence_score, confidence_band = calculate_confidence(decision)

    return {
        "Decision": decision,
        "Confidence Score": confidence_score,
        "Confidence": confidence_band,
        "Failed Gates": failed,
        "Market Cycle": classify_market_cycle(demand_supply),
        "Explanation": f"{decision} based on demand/supply score {demand_supply}"
    }
