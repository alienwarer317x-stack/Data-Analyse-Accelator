from ingestion.fundamentals_adapter import get_structural_fundamentals
from ingestion.fundamentals_adapter import evaluate_structural_gates

# ============================================================
# PROPERTY INVESTMENT ACCELERATOR — LOGIC ENGINE
# AUTHORITATIVE DECISION + NARRATIVE ENGINE
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

def calculate_demand_supply_ratio(vacancy, stock, dom):
    if vacancy is None or stock is None or dom is None:
        return None

    vacancy_component = clamp(1 - vacancy / 5.0)
    stock_component = clamp(1 - stock / 2.5)
    dom_component = clamp(1 - dom / 60.0)

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


BUY_GATE_EXPLANATIONS = {
    "Renters %": "Renter proportion sits outside the preferred 15–35% range, weakening rental stability.",
    "Vacancy": "Vacancy exceeds the 2% ceiling, indicating softer rental demand.",
    "Demand / Supply": "Demand does not sufficiently exceed supply to support price momentum.",
    "Stock on Market": "Available stock is elevated, signalling excess supply.",
    "Gross Yield": "Rental yield is below the minimum threshold for income resilience.",
    "Reliability": "Statistical reliability is insufficient for a high‑conviction decision.",
    "36m Growth Too High": "Recent growth appears unsustainably strong, elevating pullback risk.",
    "10yr CAGR Too High": "Long‑term growth rate exceeds sustainability benchmarks.",
}


# ---------------- PATH TO BUY ----------------

BUY_GATE_REQUIREMENTS = {
    "Renters %": {"type": "range", "min": 15, "max": 35, "label": "Renter proportion (%)"},
    "Vacancy": {"type": "max", "value": 2.0, "label": "Vacancy rate (%)"},
    "Demand / Supply": {"type": "min", "value": 55, "label": "Demand–Supply Ratio"},
    "Stock on Market": {"type": "max", "value": 1.3, "label": "Stock on market (%)"},
    "Gross Yield": {"type": "min", "value": 4.0, "label": "Gross rental yield (%)"},
    "Reliability": {"type": "min", "value": 51, "label": "Statistical reliability"},
}


def build_path_to_buy(factors, failed_gates):
    actions = []

    current_map = {
        "Renters %": factors.get("renters_pct"),
        "Vacancy": factors.get("vacancy_pct"),
        "Demand / Supply": factors.get("demand_supply_ratio"),
        "Stock on Market": factors.get("stock_on_market_pct"),
        "Gross Yield": factors.get("gross_rental_yield"),
        "Reliability": factors.get("statistical_reliability"),
    }

    for gate in failed_gates:
        rule = BUY_GATE_REQUIREMENTS.get(gate)
        if not rule:
            continue

        current = current_map.get(gate)

        if rule["type"] == "range":
            actions.append(
                f"{rule['label']} must move into the {rule['min']}–{rule['max']} range "
                f"(currently {current})."
            )
        elif rule["type"] == "min":
            actions.append(
                f"{rule['label']} must rise above {rule['value']} (currently {current})."
            )
        elif rule["type"] == "max":
            actions.append(
                f"{rule['label']} must fall below {rule['value']} (currently {current})."
            )

    return actions


# ---------------- GROWTH ----------------

def calculate_cagr(total_growth_pct, years):
    if total_growth_pct is None or years <= 0:
        return None
    return ((1 + total_growth_pct / 100) ** (1 / years) - 1) * 100


def consolidate_growth_metrics(row):
    values = [
        row.get("sqm_10y_growth_pct"),
        row.get("oth_10y_growth_pct"),
        row.get("htag_10y_growth_pct"),
    ]
    vals = [v for v in values if isinstance(v, (int, float))]
    avg_10y = sum(vals) / len(vals) if vals else None

    return {
        "sqm_36m_growth_pct": row.get("sqm_36m_growth_pct"),
        "avg_10y_growth_pct": avg_10y,
        "cagr_10y_pct": calculate_cagr(avg_10y, 10) if avg_10y is not None else None,
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
    
def calculate_investability_score(confidence_score, structural_status):
    penalty = {
        "PASS": 0,
        "WARN": 10,
        "FAIL": 30,
    }.get(structural_status, 0)

    return max(0, confidence_score - penalty)


# ---------------- AUTHORITATIVE NARRATIVE ----------------

def build_authoritative_narrative(decision, dsr, growth, failed_gates, structural_eval, factors):
    strengths = []
    risks = []
    gate_explanations = []

    if dsr is not None:
        if dsr >= 70:
            strengths.append("Demand materially exceeds supply, creating a tight market.")
        elif dsr >= 60:
            strengths.append("Demand exceeds supply, supporting steady conditions.")
        else:
            risks.append("Demand–supply balance is insufficient to drive growth.")

    if growth.get("cagr_10y_pct") is not None:
        if growth["cagr_10y_pct"] <= 7:
            strengths.append("Long‑term growth remains within sustainable norms.")
        else:
            risks.append("Long‑term growth exceeds sustainability benchmarks.")

    for g in failed_gates:
        explanation = BUY_GATE_EXPLANATIONS.get(g)
        if explanation:
            gate_explanations.append(explanation)

    if structural_eval["status"] == "FAIL":
        risks.append("Structural fundamentals fail long‑term investment criteria.")
    elif structural_eval["status"] == "WARN":
        risks.append("Structural fundamentals introduce elevated long‑term risk.")

    headline = (
        "Why this suburb is considered a BUY"
        if decision == "BUY"
        else "Why this suburb is assessed as an AVOID"
    )

    return {
        "headline": headline,
        "strengths": strengths,
        "risks": risks,
        "failed_gate_explanations": gate_explanations,
        "path_to_buy": build_path_to_buy(factors, failed_gates),
    }


# ---------------- AUTHORITATIVE EVALUATION ----------------

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
    failed += evaluate_growth_gates(growth)

    structural_eval = evaluate_structural_gates(
        get_structural_fundamentals(row.get("Suburb"))
    )

    if structural_eval["status"] == "FAIL":
        decision = "AVOID"

    confidence_score, confidence_band = calculate_confidence(decision)
    investability_score = calculate_investability_score(
    confidence_score,
    structural_eval["status"
    narrative = build_authoritative_narrative(
        decision=decision,
        dsr=demand_supply,
        growth=growth,
        failed_gates=failed,
        structural_eval=structural_eval,
        factors=factors,
    )

    return {
        "Decision": decision,
        "Confidence": confidence_band,
        "Confidence Score": confidence_score,
        "Investability Score": investability_score,
        "Failed Gates": failed if failed else ["None"],
        "Structural Status": structural_eval["status"],
        "Narrative": narrative,
    }
