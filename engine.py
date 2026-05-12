# ============================================================
# ENGINE CONTRACT
# ============================================================

ENGINE_NAME = "Property Investment Accelerator — Authoritative Engine"
ENGINE_STAGE = "Stage 2 (Authoritative Suburb Evaluation)"
ENGINE_VERSION = "v1.0.0"

# ============================================================
# NORMALISATION
# ============================================================

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


# ============================================================
# DEMAND → SUPPLY
# ============================================================

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


# ============================================================
# BUY GATES
# ============================================================

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

    if (
        factors["statistical_reliability"] is not None
        and factors["statistical_reliability"] <= 51
    ):
        failed.append("Reliability")

    return ("BUY" if not failed else "AVOID"), failed


# ============================================================
# GROWTH
# ============================================================

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


def triangulate_36m_growth(sqm_36m, htag_36m, typical_36m):
    values = [v for v in [sqm_36m, htag_36m, typical_36m] if isinstance(v, (int, float))]
    if len(values) < 2:
        return {"sqm_36m": sqm_36m, "htag_36m": htag_36m, "typical_36m": typical_36m,
                "avg_36m": None, "status": "INSUFFICIENT_DATA"}

    avg_36m = sum(values) / len(values)
    return {
        "sqm_36m": sqm_36m,
        "htag_36m": htag_36m,
        "typical_36m": typical_36m,
        "avg_36m": round(avg_36m, 2),
        "status": "PASS" if avg_36m < 50 else "FAIL",
    }


def calculate_cagr_from_total(total_growth_pct, years=10):
    if total_growth_pct is None:
        return None
    try:
        return ((1 + total_growth_pct / 100) ** (1 / years) - 1) * 100
    except:
        return None


def triangulate_10y_growth(sqm_cagr, oth_total_growth, htag_total_growth):
    oth_cagr = calculate_cagr_from_total(oth_total_growth)
    htag_cagr = calculate_cagr_from_total(htag_total_growth)

    values = [v for v in [sqm_cagr, oth_cagr, htag_cagr] if isinstance(v, (int, float))]
    if len(values) < 2:
        return {
            "sqm_cagr": sqm_cagr, "oth_cagr": oth_cagr, "htag_cagr": htag_cagr,
            "total_cagr": None, "alignment_gap": None, "status": "INSUFFICIENT_DATA"
        }

    total_cagr = sum(values) / len(values)
    alignment_gap = abs(oth_cagr - total_cagr) if oth_cagr is not None else None

    if total_cagr > 7:
        status = "FAIL"
    elif alignment_gap is not None and alignment_gap > 1:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "sqm_cagr": sqm_cagr,
        "oth_cagr": oth_cagr,
        "htag_cagr": htag_cagr,
        "total_cagr": round(total_cagr, 2),
        "alignment_gap": round(alignment_gap, 2) if alignment_gap else None,
        "status": status,
    }


# ============================================================
# CONFIDENCE & INVESTABILITY
# ============================================================

def calculate_confidence(decision):
    score = 85 if decision == "BUY" else 60
    return score, ("High" if score >= 75 else "Medium")


def calculate_investability_score(confidence_score, structural_status):
    status_map = {
        "BUY": "PASS", "WATCH": "WARN", "AVOID": "FAIL",
        "PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL",
    }
    normalised = status_map.get(structural_status, "PASS")
    penalty = {"PASS": 0, "WARN": 10, "FAIL": 30}.get(normalised, 0)
    return max(0, confidence_score - penalty)


# ============================================================
# STRUCTURAL SCORING (STAGE 3)
# ============================================================

def evaluate_structural_score(structural):
    results = {}
    pass_count = warn_count = fail_count = 0
    critical_fail = False

    def score(label, outcome, critical=False):
        nonlocal pass_count, warn_count, fail_count, critical_fail
        results[label] = outcome
        if outcome == "PASS":
            pass_count += 1
        elif outcome == "WARN":
            warn_count += 1
        elif outcome == "FAIL":
            fail_count += 1
            if critical:
                critical_fail = True

    # Supply
    ratio = structural.get("approval_ratio_18m")
    if ratio is not None:
        if ratio < 6:
            score("18m Approvals Ratio", "PASS", critical=True)
        elif ratio <= 8:
            score("18m Approvals Ratio", "WARN", critical=True)
        else:
            score("18m Approvals Ratio", "FAIL", critical=True)

    land = structural.get("developable_land")
    if land == "LOW":
        score("Developable Land", "PASS", critical=True)
    elif land == "MODERATE":
        score("Developable Land", "WARN", critical=True)
    elif land == "HIGH":
        score("Developable Land", "FAIL", critical=True)

    # Professional Jobs
    for year in ["2016", "2021"]:
        delta = structural.get(f"prof_occ_delta_{year}")
        if delta is not None:
            if delta > 0:
                score(f"Professional Jobs {year}", "PASS")
            elif delta == 0:
                score(f"Professional Jobs {year}", "WARN")
            else:
                score(f"Professional Jobs {year}", "FAIL")
        else:
            score(f"Professional Jobs {year}", "FAIL")

    # Income
    for year in ["2016", "2021"]:
        delta = structural.get(f"income_delta_{year}")
        if delta is not None:
            if delta > 0:
                score(f"Income Growth {year}", "PASS")
            elif delta == 0:
                score(f"Income Growth {year}", "WARN")
            else:
                score(f"Income Growth {year}", "FAIL")
        else:
            score(f"Income Growth {year}", "FAIL")

    # Stress
    rent_ok = structural.get("rent_stress_ok_pct")
    if rent_ok is not None:
        if rent_ok > 65:
            score("Rent Stress", "PASS")
        elif rent_ok >= 60:
            score("Rent Stress", "WARN")
        else:
            score("Rent Stress", "FAIL")

    mort_ok = structural.get("mortgage_stress_ok_pct")
    if mort_ok is not None:
        if mort_ok > 75:
            score("Mortgage Stress", "PASS")
        elif mort_ok >= 70:
            score("Mortgage Stress", "WARN")
        else:
            score("Mortgage Stress", "FAIL")

    # Jobs, Accessibility, Diversity, Affordability...
    jobs = structural.get("job_count")
    if jobs is not None:
        if jobs >= 500:
            score("Job Infrastructure", "PASS", critical=True)
        elif jobs >= 50:
            score("Job Infrastructure", "WARN", critical=True)
        else:
            score("Job Infrastructure", "FAIL", critical=True)

    travel = structural.get("travel_time_mins")
    if travel is not None:
        if travel < 45:
            score("Accessibility", "PASS")
        elif travel <= 60:
            score("Accessibility", "WARN")
        else:
            score("Accessibility", "FAIL")

    diversity = structural.get("employment_diversity")
    if diversity == "HIGH":
        score("Employment Diversity", "PASS")
    elif diversity == "MEDIUM":
        score("Employment Diversity", "WARN")
    elif diversity == "LOW":
        score("Employment Diversity", "FAIL")

    affordability = structural.get("affordability_band")
    if affordability == "GOOD":
        score("Housing Affordability", "PASS")
    elif affordability == "STRETCHED":
        score("Housing Affordability", "WARN")
    elif affordability == "SEVERE":
        score("Housing Affordability", "FAIL")

    # Final
    if critical_fail or fail_count >= 2:
        final = "AVOID"
    elif warn_count >= 3:
        final = "WATCH"
    else:
        final = "BUY"

    return {
        "Final": final,
        "Pass": pass_count,
        "Warn": warn_count,
        "Fail": fail_count,
        "Details": results,
    }


# ============================================================
# NARRATIVE & MAIN EVALUATION
# ============================================================

# ... (BUY_GATE_EXPLANATIONS, build_path_to_buy, build_authoritative_narrative remain the same as you had)

def evaluate_suburb(row):
    # [Your original evaluate_suburb logic with the fixes applied]
    # Make sure you paste your full evaluate_suburb function here,
    # but with the corrected structural call.

    # For now, to get the app running, here's a minimal working skeleton:
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

    # Structural (Stage 3)
    structural_data = {
        "approval_ratio_18m": 5.5,
        "developable_land": "LOW",
        "prof_occ_delta_2016": 1,
        "prof_occ_delta_2021": 2,
        "income_delta_2016": 5,
        "income_delta_2021": 3,
        "rent_stress_ok_pct": 68,
        "mortgage_stress_ok_pct": 78,
        "job_count": 620,
        "travel_time_mins": 42,
        "employment_diversity": "HIGH",
        "affordability_band": "GOOD",
    }
    structural_stage3 = evaluate_structural_score(structural_data)

    confidence_score, confidence_band = calculate_confidence(decision)
    investability_score = calculate_investability_score(confidence_score, structural_stage3["Final"])

    # ... build narrative etc.

    output = {
        "Decision": decision,
        "Confidence": confidence_band,
        "Confidence Score": confidence_score,
        "Investability Score": investability_score,
        "Demand / Supply Ratio": demand_supply,
        "Growth": {},
        "Factors": factors,
        "Failed Gates": failed if failed else ["None"],
        "Structural Status": structural_stage3["Final"],
        "Structural Stage 3": structural_stage3,
        "Narrative": {},
        "Engine Name": ENGINE_NAME,
        "Engine Stage": ENGINE_STAGE,
        "Engine Version": ENGINE_VERSION,
    }
    return output
