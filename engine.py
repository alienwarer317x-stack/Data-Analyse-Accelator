from ingestion.abs_adapter import get_abs_structural


# ============================================================
# PROPERTY INVESTMENT ACCELERATOR — LOGIC ENGINE
# AUTHORITATIVE DECISION + NARRATIVE ENGINE
# ============================================================


# ---------------- NORMALISATION ----------------
def normalise_percent(val):
    """
    Standardises input to a consistent float. 
    Assumes input like '5.5', 5.5, or '5.5%' all represent 5.5%.
    """
    if val is None or val == "":
        return None
    try:
        # Remove % and whitespace, then convert to float
        v = float(str(val).replace("%", "").strip())
        return v
    except (ValueError, TypeError):
        return None

def normalise_plain(val):
    """Standardises non-percentage numeric inputs."""
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
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
    """
    Evaluates the 'Must-Have' financial and supply metrics.
    Returns a tuple: (Decision String, List of failed gate names)
    """
    failed = []
    
    # 1. Renter Ratio (Ideally 15-35% for balanced owner-occupier appeal)
    renters = factors.get("renters_pct")
    if renters is None or not (15 <= renters <= 35):
        failed.append("Renters %")

    # 2. Vacancy Rate (Must be low, < 2%)
    vacancy = factors.get("vacancy_pct")
    if vacancy is None or vacancy >= 2.0:
        failed.append("Vacancy")

    # 3. Demand/Supply Ratio (DSR Score > 55)
    dsr = factors.get("demand_supply_ratio")
    if dsr is None or dsr <= 55:
        failed.append("Demand / Supply")

    # 4. Stock on Market (Ideally < 1.3%)
    stock = factors.get("stock_on_market_pct")
    if stock is None or stock >= 1.3:
        failed.append("Stock on Market")

    # 5. Gross Rental Yield (Ideally > 4%)
    yield_pct = factors.get("gross_rental_yield")
    if yield_pct is None or yield_pct <= 4.0:
        failed.append("Gross Yield")

    # 6. Statistical Reliability (Must be > 51)
    reliability = factors.get("statistical_reliability")
    if reliability is not None and reliability <= 51:
        failed.append("Reliability")

    decision = "BUY" if not failed else "AVOID"
    return decision, failed

BUY_GATE_EXPLANATIONS = {
    "Renters %": "Renter proportion sits outside the preferred 15–35% range, weakening rental stability.",
    "Vacancy": "Vacancy exceeds the 2% ceiling, indicating softer rental demand.",
    "Demand / Supply": "Demand does not sufficiently exceed supply to support price momentum.",
    "Stock on Market": "Available stock is elevated, signalling excess supply.",
    "Gross Yield": "Rental yield is below the minimum threshold for income resilience.",
    "Reliability": "Statistical reliability is insufficient for a high‑conviction decision.",
    "36m Growth Too High": "Recent growth appears unsustainably strong, elevating pullback risk.",
    "10yr CAGR Too High": "Long‑term growth rate exceeds sustainability benchmarks.",
    "36m Growth > 50%": (
        "Triangulated 36‑month price growth exceeds 50%, "
        "indicating an overheated market with elevated pullback risk."),
    "10yr CAGR Alignment Issue": (
        "Cross-source 10‑year growth estimates diverge materially, "
        "indicating potential data inconsistency. Suburb requires review."),
}


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
    if growth["cagr_10y_pct"] is not None and growth["cagr_10y_pct"] > 7:
        failed.append("10yr CAGR Too High")
    return failed


def calculate_cagr_from_total(total_growth_pct, years=10):
    if total_growth_pct is None:
        return None
    try:
        return ((1 + total_growth_pct / 100) ** (1 / years) - 1) * 100
    except:
        return None


def triangulate_36m_growth(sqm_36m, htag_36m, typical_36m):
    values = [v for v in [sqm_36m, htag_36m, typical_36m] if isinstance(v, (int, float))]
    if len(values) < 2:
        return {
            "sqm_36m": sqm_36m,
            "htag_36m": htag_36m,
            "typical_36m": typical_36m,
            "avg_36m": None,
            "status": "INSUFFICIENT_DATA",
        }
    avg_36m = sum(values) / len(values)
    return {
        "sqm_36m": sqm_36m,
        "htag_36m": htag_36m,
        "typical_36m": typical_36m,
        "avg_36m": round(avg_36m, 2),
        "status": "PASS" if avg_36m < 50 else "FAIL",
    }


def triangulate_10y_growth(sqm_cagr, oth_total_growth, htag_total_growth):
    # Ensure inputs are numbers using our new normalisers
    sqm_c = normalise_percent(sqm_cagr)
    oth_c = calculate_cagr_from_total(oth_total_growth)
    htag_c = calculate_cagr_from_total(htag_total_growth)
    
    # Filter for valid numbers
    values = [v for v in [sqm_c, oth_c, htag_c] if v is not None]
    
    if len(values) < 2:
        return {
            "sqm_cagr": sqm_c, "oth_cagr": oth_c, "htag_cagr": htag_c,
            "total_cagr": None, "alignment_gap": None, "status": "INSUFFICIENT_DATA"
        }
    
    total_cagr = sum(values) / len(values)
    
    # Calculate gap based on the source most likely to vary (oth_c)
    alignment_gap = abs(oth_c - total_cagr) if (oth_c is not None and total_cagr is not None) else 0

    # Logic Gates
    if total_cagr > 7.0:
        status = "FAIL" # Overheated
    elif alignment_gap > 2.5: 
        status = "REVIEW" # Data conflict
    else:
        status = "PASS"

    return {
        "sqm_cagr": sqm_c,
        "oth_cagr": oth_c,
        "htag_cagr": htag_c,
        "total_cagr": round(total_cagr, 2),
        "alignment_gap": round(alignment_gap, 2),
        "status": status,
    }


# ---------------- CONFIDENCE ----------------
def calculate_confidence(decision):
    score = 85 if decision == "BUY" else 60
    return score, ("High" if score >= 75 else "Medium")


def calculate_investability_score(confidence_score, structural_status):
    penalty = {"PASS": 0, "WARN": 10, "FAIL": 30}.get(structural_status, 0)
    return max(0, confidence_score - penalty)


# ---------------- AUTHORITATIVE NARRATIVE ----------------
def build_authoritative_narrative(decision, dsr, growth, failed_gates, structural_eval, factors):
    strengths = []
    risks = []
    gate_explanations = []

    # 1. Demand/Supply Balance
    if dsr is not None:
        if dsr >= 70:
            strengths.append("High Conviction: Demand materially exceeds supply, creating a tight seller's market.")
        elif dsr >= 60:
            strengths.append("Healthy Balance: Demand exceeds supply, supporting steady price growth.")
        else:
            risks.append("Supply Risk: Demand–supply balance is currently insufficient to drive short-term growth.")

    # 2. Growth Sustainability (Minimum Criteria: <= 7% CAGR)
    # Using the 'total_cagr' key from our triangulation logic
    cagr = growth.get("total_cagr")
    if cagr is not None:
        if cagr <= 7.0:
            strengths.append(f"Sustainable Growth: Long-term growth ({cagr}%) is within healthy historical norms.")
        else:
            risks.append(f"Overheated: 10-year growth ({cagr}%) exceeds sustainability benchmarks, suggesting a cycle peak.")

    # 3. Structural Stage 3 Assessment
    # Mapped to the 'Final' key and new BUY/WATCH/AVOID statuses
    struct_status = structural_eval.get("Final")
    if struct_status == "BUY":
        strengths.append("Strong Fundamentals: Professional growth and income deltas support long-term value.")
    elif struct_status == "AVOID":
        risks.append("Structural Failure: Critical risks identified in supply approvals or employment diversity.")
    elif struct_status == "WATCH":
        risks.append("Elevated Risk: Structural metrics (Income/Stress) require close monitoring.")

    # 4. Map Failed Gates to explanations
    for g in failed_gates:
        explanation = BUY_GATE_EXPLANATIONS.get(g)
        if explanation:
            gate_explanations.append(explanation)

    # 5. Determine Headline Strategy
    if decision == "BUY":
        headline = "Why this suburb is considered a BUY"
    elif decision == "HOLD":
        headline = "Neutral Assessment: This suburb is a HOLD / REVIEW"
    else:
        headline = "Why this suburb is assessed as an AVOID"

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

    # --- 36-MONTH GROWTH HARD GATE (STAGE 2) ---
    tri_36m = triangulate_36m_growth(
        sqm_36m=row.get("sqm_36m_growth_pct"),
        htag_36m=row.get("htag_36m_growth_pct"),
        typical_36m=row.get("typical_36m_growth_pct"),
    )
    if tri_36m["status"] == "FAIL":
        failed.append("36m Growth > 50%")
        decision = "AVOID"

    # --- 10-YEAR GROWTH HARD GATE (STAGE 2) ---
    tri_10y = triangulate_10y_growth(
        sqm_cagr=row.get("sqm_10y_gr_pa"),
        oth_total_growth=row.get("oth_10y_growth"),
        htag_total_growth=row.get("htag_10y_growth"),
    )
    if tri_10y["status"] == "FAIL":
        failed.append("10yr CAGR > 7%")
        decision = "AVOID"
    elif tri_10y["status"] == "REVIEW":
        failed.append("10yr CAGR Alignment Issue")
        if decision == "BUY":
            decision = "HOLD"
# ---------------- STAGE 3 – STRUCTURAL SCORING ----------------
    abs_data = get_abs_structural(row.get("Suburb"))

    structural_data = {
        # 1. Development & Supply (Real data from AreaSearch/CSV)
        "approval_ratio_18m": normalise_plain(row.get("Approvals per 1,000 People (2yr)")),
        "developable_land": row.get("Development Drivers Ranking", "MODERATE"),
        
        # 2. Socio-Economic Deltas (From your optimized ABS adapter)
        "prof_occ_delta_2016": abs_data.get("prof_occ_delta_2016"),
        "prof_occ_delta_2021": abs_data.get("prof_occ_delta_2021"),
        "income_delta_2016": abs_data.get("income_delta_2016"),
        "income_delta_2021": abs_data.get("income_delta_2021"),
        
        # 3. Financial Resilience (From your optimized ABS adapter)
        "rent_stress_ok_pct": abs_data.get("rent_stress_ok_pct"),
        "mortgage_stress_ok_pct": abs_data.get("mortgage_stress_ok_pct"),
        
        # 4. Job Infrastructure & Context (Real data from AreaSearch/CSV)
        "job_count": normalise_plain(row.get("Total Employment")),
        "travel_time_mins": normalise_plain(row.get("Persons per Square Kilometer")), 
        "employment_diversity": row.get("AS Employment Drivers Ranking", "MEDIUM"),
        "affordability_band": row.get("AS Income Ranking", "STRETCHED"),
    }

    # The rest of your logic remains the same but now uses REAL data
    structural_stage3 = evaluate_structural_score(structural_data)

    confidence_score, confidence_band = calculate_confidence(decision)
    investability_score = calculate_investability_score(
        confidence_score, structural_stage3["Final"]
    )

    narrative = build_authoritative_narrative(
        decision=decision,
        dsr=demand_supply,
        growth=growth,
        failed_gates=failed,
        structural_eval={"status": structural_stage3["Final"]},
        factors=factors,
    )

    return {
        "Decision": decision,
        "Confidence": confidence_band,
        "Confidence Score": confidence_score,
        "Investability Score": investability_score,
        "Demand / Supply Ratio": demand_supply,
        "Failed Gates": failed if failed else ["None"],
        "Structural Status": structural_stage3["Final"],
        "Structural Stage 3": structural_stage3,
        "Narrative": narrative,
    }

# ============================================================
# STAGE 3 — STRUCTURAL SCORING
# ============================================================
def evaluate_structural_score(structural):
    """
    Evaluates suburb-level structural durability using Stage 3 rules.
    """
    results = {}
    pass_count = 0
    warn_count = 0
    fail_count = 0
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

    # ---------- SUPPLY & LAND ----------
    ratio = structural.get("approval_ratio_18m")
    if ratio is not None:
        if ratio < 6:
            score("18m Approvals Ratio", "PASS", critical=True)
        elif ratio <= 8:
            score("18m Approvals Ratio", "WARN", critical=True)
        else:
            score("18m Approvals Ratio", "FAIL", critical=True)

    # Use .upper() and 'in' to catch variations like "Low" or "Constrained"
    land = str(structural.get("developable_land") or "").upper()
    if any(x in land for x in ["LOW", "CONSTRAINED", "LIMITED"]):
        score("Developable Land", "PASS", critical=True)
    elif "MODERATE" in land:
        score("Developable Land", "WARN", critical=True)
    elif "HIGH" in land or land != "":
        score("Developable Land", "FAIL", critical=True)

    # ---------- EMPLOYMENT QUALITY & INCOME ----------
    for year in ["2016", "2021"]:
        for metric in ["prof_occ_delta", "income_delta"]:
            key = f"{metric}_{year}"
            val = structural.get(key)
            label = "Professional Jobs" if "prof" in metric else "Income Growth"
            if val is not None:
                if val > 0:
                    score(f"{label} {year}", "PASS")
                elif val == 0:
                    score(f"{label} {year}", "WARN")
                else:
                    score(f"{label} {year}", "FAIL")

    # ---------- FINANCIAL RESILIENCE ----------
    rent_ok = structural.get("rent_stress_ok_pct")
    if rent_ok is not None:
        if rent_ok > 65: score("Rent Stress", "PASS")
        elif rent_ok >= 60: score("Rent Stress", "WARN")
        else: score("Rent Stress", "FAIL")

    mort_ok = structural.get("mortgage_stress_ok_pct")
    if mort_ok is not None:
        if mort_ok > 75: score("Mortgage Stress", "PASS")
        elif mort_ok >= 70: score("Mortgage Stress", "WARN")
        else: score("Mortgage Stress", "FAIL")

    # ---------- JOB INFRASTRUCTURE & ACCESSIBILITY ----------
    jobs = structural.get("job_count")
    if jobs is not None:
        if jobs >= 500: score("Job Infrastructure", "PASS", critical=True)
        elif jobs >= 50: score("Job Infrastructure", "WARN", critical=True)
        else: score("Job Infrastructure", "FAIL", critical=True)

    travel = structural.get("travel_time_mins")
    if travel is not None:
        if travel < 45: score("Accessibility", "PASS")
        elif travel <= 60: score("Accessibility", "WARN")
        else: score("Accessibility", "FAIL")

    # ---------- DIVERSITY & AFFORDABILITY (String Checks) ----------
    diversity = str(structural.get("employment_diversity") or "").upper()
    if "HIGH" in diversity: score("Employment Diversity", "PASS")
    elif "MEDIUM" in diversity or "MODERATE" in diversity: score("Employment Diversity", "WARN")
    elif "LOW" in diversity: score("Employment Diversity", "FAIL")

    affordability = str(structural.get("affordability_band") or "").upper()
    if "GOOD" in affordability: score("Housing Affordability", "PASS")
    elif "STRETCHED" in affordability: score("Housing Affordability", "WARN")
    elif "SEVERE" in affordability: score("Housing Affordability", "FAIL")

    # ---------- FINAL CLASSIFICATION ----------
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
        "Details": results
    }
