# ============================================================
# PROPERTY INVESTMENT ACCELERATOR — AUTHORITATIVE LOGIC ENGINE
# ============================================================

# ---------------- NORMALISATION ----------------
def normalise_plain(val):
    try:
        return float(str(val).replace("%", "").replace("days", "").strip())
    except Exception:
        return None


def normalise_percent(val):
    try:
        v = float(str(val).replace("%", "").strip())
        return v * 100 if v <= 1 else v
    except Exception:
        return None


def clamp(value, lower=0.0, upper=1.0):
    return max(lower, min(value, upper))


# ---------------- DEMAND / SUPPLY ----------------
def calculate_demand_supply_ratio(
    vacancy_pct: float,
    stock_on_market_pct: float,
    days_on_market: int,
    dom_long_term_avg: int = 60,
    vacancy_upper_bound: float = 5.0,
    som_upper_bound: float = 2.5
) -> float:
    """
    Returns a Demand–Supply Ratio score between 0 and 100.
    """

    if (
        vacancy_pct is None or
        stock_on_market_pct is None or
        days_on_market is None or
        dom_long_term_avg is None or
        dom_long_term_avg <= 0
    ):
        return None

    vacancy_score = clamp(1 - (vacancy_pct / vacancy_upper_bound))
    stock_score = clamp(1 - (stock_on_market_pct / som_upper_bound))
    dom_score = clamp(1 - (days_on_market / dom_long_term_avg))

    raw_score = (
        0.40 * vacancy_score +
        0.35 * stock_score +
        0.25 * dom_score
    )

    return round(raw_score * 100, 1)


# ---------------- BUY / AVOID GATES ----------------
def evaluate_buy_gates(factors):
    failed = []

    renters = factors.get("renters_pct")
    vacancy = factors.get("vacancy_pct")
    demand = factors.get("demand_supply_ratio")
    stock = factors.get("stock_on_market_pct")
    yield_pct = factors.get("gross_rental_yield")
    reliability = factors.get("statistical_reliability")

    if renters is None or not (15 <= renters <= 35):
        failed.append("Renters %")

    if vacancy is None or vacancy >= 2:
        failed.append("Vacancy")

    if demand is None or demand <= 55:
        failed.append("Demand / Supply")

    if stock is None or stock >= 1.3:
        failed.append("Stock on Market")

    if yield_pct is None or yield_pct <= 4:
        failed.append("Gross Yield")

    if reliability is None or reliability <= 51:
        failed.append("Reliability")

    return ("BUY" if not failed else "AVOID"), failed


# ---------------- CONFIDENCE ----------------
def calculate_confidence(decision, failed_gates):
    if decision == "BUY":
        base = 85
    else:
        base = 60 - min(len(failed_gates) * 5, 20)

    band = (
        "High" if base >= 75
        else "Medium" if base >= 60
        else "Low"
    )

    return base, band


def demand_confidence_penalty(score):
    if score is None:
        return 15
    if score < 40:
        return 20
    if score < 50:
        return 10
    if score < 55:
        return 5
    return 0


# ---------------- MARKET CYCLE ----------------
def classify_market_cycle(score, vacancy, stock):
    vacancy = vacancy or 5
    stock = stock or 3

    if score >= 70 and stock < 1.0:
        return "Expansion"
    if score >= 60 and vacancy < 2.0:
        return "Early Upswing"
    if score >= 60 and stock >= 1.5:
        return "Late Cycle / Peak"
    if score < 45 and stock > 2.0:
        return "Downturn"
    return "Stagnation"


# ---------------- NARRATIVE ----------------
def generate_narrative(decision, score, vacancy, stock, dom, yield_pct, band, failed):
    v = f"{vacancy:.1f}%" if vacancy is not None else "?"
    s = f"{stock:.1f}%" if stock is not None else "?"
    d = f"{dom:.0f} days" if dom is not None else "?"
    y = f"{yield_pct:.1f}%" if yield_pct is not None else "?"

    if decision == "BUY":
        return (
            f"Strong demand relative to supply (score {score}). "
            f"Vacancy {v}, stock {s}, days on market {d}. "
            f"Yield {y}. Confidence: {band}."
        )

    return (
        f"Insufficient demand (score {score}). "
        f"Failed gates: {', '.join(failed)}. "
        f"Vacancy {v}, stock {s}, days {d}, yield {y}. "
        f"Confidence: {band}."
    )


# ---------------- PUBLIC ENTRY POINT ----------------
def evaluate_suburb(row):
    """
    SINGLE authoritative Stage 2 entry point.
    app.py should ONLY call this function.
    """

    vacancy = normalise_plain(row.get("Vacancy rate"))
    stock = normalise_plain(row.get("Percent stock on market"))
    dom = normalise_plain(row.get("Days on market"))
    yield_pct = normalise_percent(row.get("Gross rental yield"))

    demand_score = calculate_demand_supply_ratio(vacancy, stock, dom)

    decision, failed = evaluate_buy_gates({
        "renters_pct": normalise_percent(row.get("Percent renters in market")),
        "vacancy_pct": vacancy,
        "demand_supply_ratio": demand_score,
        "stock_on_market_pct": stock,
        "gross_rental_yield": yield_pct,
        "statistical_reliability": normalise_plain(row.get("Statistical reliability")),
    })

    base_score, _ = calculate_confidence(decision, failed)
    final_score = max(0, base_score - demand_confidence_penalty(demand_score))

    final_band = (
        "High" if final_score >= 85
        else "Medium" if final_score >= 65
        else "Low"
    )

    return {
        "Decision": decision,
        "Failed Gates": failed,
        "Confidence Score": final_score,
        "Confidence": final_band,
        "Market Cycle": classify_market_cycle(demand_score or 0, vacancy, stock),
        "Explanation": generate_narrative(
            decision, demand_score, vacancy, stock, dom, yield_pct, final_band, failed
        ),
        "Demand Score": demand_score,
    }
