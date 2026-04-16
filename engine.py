# ============================================================
# PROPERTY INVESTMENT ACCELERATOR — LOGIC ENGINE
# Step 2: Demand → Supply implemented
# ============================================================


# ---------------- NORMALISATION ----------------

def normalise_percent(val):
    """
    Normalises percentage-like values.
    Examples:
      0.24   -> 24
      24     -> 24
      '24%'  -> 24
    """
    if val is None:
        return None
    try:
        v = float(str(val).replace("%", "").strip())
        return v * 100 if v <= 1 else v
    except:
        return None


def normalise_plain(val):
    """
    Normalises numeric / index values:
    vacancy %, stock %, DOM, reliability, etc.
    """
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


# ---------------- DEMAND → SUPPLY (DERIVED) ----------------

def calculate_demand_supply_ratio(
    vacancy_rate,
    stock_on_market,
    days_on_market,
    vacancy_upper_bound=5.0,
    stock_upper_bound=2.5,
    dom_long_term_avg=60.0,
):
    """
    Computes Demand → Supply score in range 0–100.

    Inputs (from _row):
      vacancy_rate        : % (lower = stronger demand)
      stock_on_market     : % (lower = tighter supply)
      days_on_market      : days (lower = faster absorption)

    Returns:
      float score (0–100) or None if insufficient data
    """

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


# ---------------- BUY / AVOID GATES ----------------

def evaluate_buy_gates(factors):
    """
    Canonical BUY gate logic.
    Returns:
      decision (BUY / AVOID)
      failed_gates (list)
    """

    failed = []

    renters_pct = factors.get("renters_pct")
    vacancy_pct = factors.get("vacancy_pct")
    demand_supply_ratio = factors.get("demand_supply_ratio")
    stock_pct = factors.get("stock_on_market_pct")
    yield_pct = factors.get("gross_rental_yield")
    reliability = factors.get("statistical_reliability")

    if renters_pct is None or not (15 <= renters_pct <= 35):
        failed.append("Renters %")

    if vacancy_pct is None or vacancy_pct >= 2:
        failed.append("Vacancy")

    if demand_supply_ratio is None or demand_supply_ratio <= 55:
        failed.append("Demand / Supply")

    if stock_pct is None or stock_pct >= 1.3:
        failed.append("Stock on Market")

    if yield_pct is None or yield_pct <= 4:
        failed.append("Gross Yield")

    if reliability is None or reliability <= 51:
        failed.append("Reliability")

    decision = "BUY" if not failed else "AVOID"
    return decision, failed


# ---------------- CONFIDENCE ----------------

def calculate_confidence(decision):
    """
    Deterministic confidence logic (Step 4 will extend this).
    """
    score = 85 if decision == "BUY" else 60
    band = "High" if score >= 75 else "Medium"
    return score, band


# ---------------- MARKET CYCLE ----------------

def classify_market_cycle(demand_supply_ratio):
    if demand_supply_ratio is None:
        return "Unknown"
    if demand_supply_ratio >= 70:
        return "Expansion"
    if demand_supply_ratio >= 60:
        return "Upswing"
    if demand_supply_ratio >= 50:
        return "Stagnation"
    return "Downturn"


# ---------------- SINGLE AUTHORITATIVE ENTRY ----------------

def evaluate_suburb(row):
    """
    Stage 2 authoritative entry point.
    Consumes a _row dict matching the locked data contract.
    """

    vacancy = normalise_plain(row.get("Vacancy rate"))
    stock = normalise_plain(row.get("Percent stock on market"))
    dom = normalise_plain(row.get("Days on market"))
    yield_pct = normalise_percent(row.get("Gross rental yield"))
    renters_pct = normalise_percent(row.get("Percent renters in market"))
    reliability = normalise_plain(row.get("Statistical reliability"))

    demand_supply = calculate_demand_supply_ratio(
        vacancy_rate=vacancy,
        stock_on_market=stock,
        days_on_market=dom,
    )

    factors = {
        "renters_pct": renters_pct,
        "vacancy_pct": vacancy,
        "demand_supply_ratio": demand_supply,
        "stock_on_market_pct": stock,
        "gross_rental_yield": yield_pct,
        "statistical_reliability": reliability,
    }

    # -----------------------------------
# Growth logic integration
# -----------------------------------
growth = consolidate_growth_metrics(row)
growth_failed = evaluate_growth_gates(growth)

decision, failed = evaluate_buy_gates(factors)

# Merge growth failures
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
    }
# -----------------------------------
# Growth helpers
# -----------------------------------
def calculate_cagr(total_growth_pct, years):
    """
    Converts total growth % into CAGR.
    Example: 80% over 10 years -> ~6.0%
    """
    if total_growth_pct is None or years <= 0:
        return None
    try:
        return ((1 + total_growth_pct / 100) ** (1 / years) - 1) * 100
    except Exception:
        return None

def consolidate_growth_metrics(row):
    """
    Consolidates growth metrics from SQM, OTH, HTAG.
    Returns derived growth indicators.
    """

    sqm_36m = row.get("sqm_36m_growth_pct")
    sqm_10y = row.get("sqm_10y_growth_pct")
    oth_10y = row.get("oth_10y_growth_pct")
    htag_10y = row.get("htag_10y_growth_pct")

    avg_10y_growth = None
    ten_year_vals = [v for v in [sqm_10y, oth_10y, htag_10y] if isinstance(v, (int, float))]
    if ten_year_vals:
        avg_10y_growth = sum(ten_year_vals) / len(ten_year_vals)

    cagr_10y = calculate_cagr(avg_10y_growth, 10) if avg_10y_growth is not None else None

    return {
        "sqm_36m_growth_pct": sqm_36m,
        "avg_10y_growth_pct": avg_10y_growth,
        "cagr_10y_pct": cagr_10y,
    }

def evaluate_growth_gates(growth):
    """
    Applies growth discipline rules.
    """

    failed = []

    # 36 month boom control
    if growth["sqm_36m_growth_pct"] is not None and growth["sqm_36m_growth_pct"] > 50:
        failed.append("36m Growth Too High")

    # 10 year sustainability check
    if growth["cagr_10y_pct"] is not None and growth["cagr_10y_pct"] > 7:
        failed.append("10yr CAGR Too High")

    return failed
