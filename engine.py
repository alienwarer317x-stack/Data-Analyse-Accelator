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
    (vacancy %, stock %, demand-supply, reliability)
    """
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return None


def evaluate_buy_gates(factors):
    """
    Core BUY gate logic.
    Returns:
      decision (BUY / AVOID)
      failed_gates (list)
    """

    failed_gates = []

    if factors.get("renters_pct") is None or not (15 <= factors["renters_pct"] <= 35):
        failed_gates.append("Renters %")

    if factors.get("vacancy_pct") is None or factors["vacancy_pct"] >= 2:
        failed_gates.append("Vacancy")

    if factors.get("demand_supply_ratio") is None or factors["demand_supply_ratio"] <= 55:
        failed_gates.append("Demand / Supply")

    if factors.get("stock_on_market_pct") is None or factors["stock_on_market_pct"] >= 1.3:
        failed_gates.append("Stock on Market")

    if factors.get("gross_rental_yield") is None or factors["gross_rental_yield"] <= 4:
        failed_gates.append("Gross Yield")

    if factors.get("statistical_reliability") is None or factors["statistical_reliability"] <= 51:
        failed_gates.append("Reliability")

    decision = "BUY" if not failed_gates else "AVOID"

    return decision, failed_gates


def calculate_confidence(decision):
    """
    Simple, deterministic confidence logic.
    Expanded later with coverage and reliability.
    """
    score = 85 if decision == "BUY" else 60
    band = "High" if score >= 75 else "Medium"
    return score, band
