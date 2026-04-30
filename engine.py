from ingestion.abs_adapter import get_abs_structural


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


# ---------------- STAGE 1 — BUY GATES ----------------

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
    "36m Growth > 50%": "Triangulated 36‑month price growth exceeds 50%, indicating an overheated market.",
    "10yr CAGR > 7%": "Long‑term growth exceeds sustainability benchmarks.",
    "10yr CAGR Alignment Issue": "Cross‑source growth estimates diverge materially, requiring review."
}


# ---------------- GROWTH HELPERS ----------------

def calculate_cagr(total_growth_pct, years):
    if total_growth_pct is None or years <= 0:
        return None
    return ((1 + total_growth_pct / 100) ** (1 / years) - 1) * 100


# ---------------- STAGE 2 — GROWTH ----------------

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


def calculate_cagr_from_total(total_growth_pct, years=10):
    if total_growth_pct is None:
        return None
    try:
        return calculate_cagr(total_growth_pct, years)
    except:
        return None


def triangulate_36m_growth(sqm_36m, htag_36m, typical_36m):
    values = [v for v in [sqm_36m, htag_36m, typical_36m] if isinstance(v, (int, float))]

    if len(values) < 2:
        return {"avg_36m": None, "status": "INSUFFICIENT_DATA"}

    avg = sum(values) / len(values)
    return {
        "avg_36m": round(avg, 2),
        "status": "PASS" if avg < 50 else "FAIL"
    }


def triangulate_10y_growth(sqm_cagr, oth_total, htag_total):
    oth_cagr = calculate_cagr_from_total(oth_total)
    htag_cagr = calculate_cagr_from_total(htag_total)

    values = [v for v in [sqm_cagr, oth_cagr, htag_cagr] if isinstance(v, (int, float))]

    if len(values) < 2:
        return {"status": "INSUFFICIENT_DATA"}

    total = sum(values) / len(values)
    gap = abs(oth_cagr - total) if oth_cagr is not None else None

    if total > 7:
        status = "FAIL"
    elif gap is not None and gap > 1:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "total_cagr": round(total, 2),
        "alignment_gap": round(gap, 2) if gap else None,
        "status": status
    }


# ---------------- STAGE 3 — STRUCTURAL SCORING ----------------

def evaluate_structural_score(structural):
    pass_count = warn_count = fail_count = 0
    critical_fail = False
    details = {}

    def score(name, result, critical=False):
        nonlocal pass_count, warn_count, fail_count, critical_fail
        details[name] = result
        if result == "PASS":
            pass_count += 1
        elif result == "WARN":
            warn_count += 1
        else:
            fail_count += 1
            if critical:
                critical_fail = True

    jobs = structural.get("job_count")
    if jobs is not None:
        if jobs >= 500:
            score("Jobs", "PASS", True)
        elif jobs >= 50:
            score("Jobs", "WARN", True)
        else:
            score("Jobs", "FAIL", True)

    rent = structural.get("rent_stress_ok_pct")
    if rent is not None:
        if rent > 65:
            score("Rent Stress", "PASS")
        elif rent >= 60:
            score("Rent Stress", "WARN")
        else:
            score("Rent Stress", "FAIL")

    mortgage = structural.get("mortgage_stress_ok_pct")
    if mortgage is not None:
        if mortgage > 75:
            score("Mortgage Stress", "PASS")
        elif mortgage >= 70:
            score("Mortgage Stress", "WARN")
        else:
            score("Mortgage Stress", "FAIL")

    final = "AVOID" if critical_fail or fail_count >= 2 else "WATCH" if warn_count >= 3 else "BUY"

    return {
        "Final": final,
        "Pass": pass_count,
        "Warn": warn_count,
        "Fail": fail_count,
        "Details": details
    }


# ---------------- FINAL AUTHORITATIVE EVALUATION ----------------

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

    tri_36m = triangulate_36m_growth(
        row.get("sqm_36m_growth_pct"),
        row.get("htag_36m_growth_pct"),
        row.get("typical_36m_growth_pct"),
    )
    if tri_36m["status"] == "FAIL":
        decision = "AVOID"

    tri_10y = triangulate_10y_growth(
        row.get("sqm_10y_gr_pa"),
        row.get("oth_10y_growth"),
        row.get("htag_10y_growth"),
    )
    if tri_10y["status"] == "FAIL":
        decision = "AVOID"
    elif tri_10y["status"] == "REVIEW" and decision == "BUY":
        decision = "HOLD"

    abs_data = get_abs_structural(row.get("Suburb"))

    structural = {
        "rent_stress_ok_pct": abs_data.get("rent_stress_ok_pct"),
        "mortgage_stress_ok_pct": abs_data.get("mortgage_stress_ok_pct"),
        "job_count": 620,
    }

    stage3 = evaluate_structural_score(structural)

    return {
        "Decision": decision,
        "Demand / Supply Ratio": demand_supply,
        "Structural Stage 3": stage3,
    }
