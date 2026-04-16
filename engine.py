============================================================
# PROPERTY INVESTMENT ACCELERATOR — LOGIC ENGINE
# Growth + Demand/Supply + Discipline (AUTHORITATIVE)
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


# ---------------- GROWTH HELPERS ----------------

def calculate_cagr(total_growth_pct, years):
    if total_growth_pct is None or years <= 0:
        return None
    try:
        return ((1 + total_growth_pct / 100) ** (1 / years) - 1) * 100
    except:
        return None


def consolidate_growth_metrics(row):
    sqm_36m = row.get("sqm_36m_growth_pct")
    sqm_10y = row.get("sqm_10y_growth_pct")
    oth_10y = row.get("oth_10y_growth_pct")
    htag_10y = row.get("htag_10y_growth_pct")

    avg_10y = None
    values = [v for v in [sqm_10y, oth_10y, htag_10y] if isinstance(v, (int, float))]
    if values:
        avg_10y = sum(values) / len(values)

    cagr_10y = calculate_cagr(avg_10y, 10) if avg_10y is not None else None

    return {
        "sqm_36m_growth_pct": sqm_36m,
        "avg_10y_growth_pct": avg_10y,
        "cagr_10y_pct": cagr_10y,
    }


def evaluate_growth_gates(growth):
    failed = []

    if growth["sqm_36m_growth_pct"] is not None and growth["sqm_36m_growth_pct"] > 50:
        failed.append("36m Growth Too High")

    if growth["cagr_10y_pct"] is not None and growth["cagr_10y_pct"] > 7:
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


# ---------------- AUTHORITATIVE ENTRY ----------------
def build_narrative(row, decision, growth, demand_supply):
    """
    Builds a structured explanation of WHY a suburb is BUY or AVOID.
    """

    strengths = []
    risks = []

    vacancy = row.get("Vacancy rate")
    stock = row.get("Percent stock on market")
    renters = row.get("Percent renters in market")
    yield_pct = row.get("Gross rental yield")

    sqm_36m = growth.get("sqm_36m_growth_pct")
    cagr_10y = growth.get("cagr_10y_pct")

    # ---- Demand / Supply ----
    if demand_supply is not None:
        if demand_supply >= 70:
            strengths.append("Demand is significantly stronger than supply, indicating a tight market.")
        elif demand_supply >= 60:
            strengths.append("Demand is stronger than supply, supporting price and rental growth.")
        else:
            risks.append("Demand–supply balance is relatively weak and may limit near‑term growth.")

    # ---- Vacancy ----
    if vacancy is not None:
        if vacancy < 1:
            strengths.append("Vacancy rates are extremely low, indicating strong rental pressure.")
        elif vacancy < 2:
            strengths.append("Vacancy rates are low, supporting rental stability.")
        else:
            risks.append("Higher vacancy rates suggest softer rental demand.")

    # ---- Stock on Market ----
    if stock is not None:
        if stock < 1:
            strengths.append("Very low stock on market suggests limited available supply.")
        elif stock > 1.3:
            risks.append("Elevated stock levels may place downward pressure on pricing.")

    # ---- Rental Yield ----
    if yield_pct is not None:
        if yield_pct >= 5:
            strengths.append("Gross rental yield is healthy, supporting cash‑flow resilience.")
        elif yield_pct < 4:
            risks.append("Rental yield is low, increasing reliance on capital growth.")

    # ---- Renters ----
    if renters is not None:
        if 20 <= renters <= 35:
            strengths.append("A stable renter population supports ongoing rental demand.")
        else:
            risks.append("Renter proportion falls outside the preferred stability range.")

    # ---- Growth Discipline ----
    if sqm_36m is not None and sqm_36m > 50:
        risks.append("Recent growth has been strong, increasing the risk of a short‑term pullback.")

    if cagr_10y is not None:
        if cagr_10y > 7:
            risks.append("Long‑term growth rate exceeds sustainable levels.")
        else:
            strengths.append("Long‑term growth has been steady and sustainable.")

    headline = (
        "Why this suburb is considered a BUY"
        if decision == "BUY"
        else "Why this suburb is currently assessed as an AVOID"
    )

    return {
        "headline": headline,
        "strengths": strengths,
        "risks": risks
    }
    
def evaluate_suburb(row):
    vacancy = normalise_plain(row.get("Vacancy rate"))
    stock = normalise_plain(row.get("Percent stock on market"))
    dom = normalise_plain(row.get("Days on market"))
    yield_pct = normalise_percent(row.get("Gross rental yield"))
    renters_pct = normalise_percent(row.get("Percent renters in market"))
    reliability = normalise_plain(row.get("Statistical reliability"))

    demand_supply = calculate_demand_supply_ratio(vacancy, stock, dom)

    factors = {
        "renters_pct": renters_pct,
        "vacancy_pct": vacancy,
        "demand_supply_ratio": demand_supply,
        "stock_on_market_pct": stock,
        "gross_rental_yield": yield_pct,
        "statistical_reliability": reliability,
    }

    decision, failed = evaluate_buy_gates(factors)

    growth = consolidate_growth_metrics(row)
    growth_failed = evaluate_growth_gates(growth)

    failed = failed + growth_failed
    if failed:
        decision = "AVOID"

    confidence_score, confidence_band = calculate_confidence(decision)

    return {
        "Decision": decision,
        "Confidence": confidence_band,
        "Confidence Score": confidence_score,
        "Demand / Supply Ratio": demand_supply,
        "Market Cycle": classify_market_cycle(demand_supply),
        "Failed Gates": failed if failed else ["None"],
        "Growth": growth,
    }
