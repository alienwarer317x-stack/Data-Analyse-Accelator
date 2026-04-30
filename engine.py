from ingestion.fundamentals_adapter import get_structural_fundamentals
from ingestion.fundamentals_adapter import evaluate_structural_gates
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
    "36m Growth > 50%": (
    "Triangulated 36‑month price growth exceeds 50%, "
    "indicating an overheated market with elevated pullback risk."),
    "10yr CAGR Alignment Issue": (
    "Cross-source 10‑year growth estimates diverge materially, "
    "indicating potential data inconsistency. Suburb requires review."),

}


# ---------------- PATH TO BUY (STEP 1) ----------------

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

    # 36-month growth is handled exclusively via triangulation
    # AVG GR 3yrs (SQM + HTAG + Typical) < 50%

    if growth["cagr_10y_pct"] is not None and growth["cagr_10y_pct"] > 7:
        failed.append("10yr CAGR Too High")

    return failed
# ---------------- 10-YEAR CAGR HELPERS ----------------

def calculate_cagr_from_total(total_growth_pct, years=10):
    """
    Convert TOTAL growth (%) into CAGR (%).
    Excel equivalent: (1 + total_growth)^(1/years) - 1
    """
    if total_growth_pct is None:
        return None
    try:
        return ((1 + total_growth_pct / 100) ** (1 / years) - 1) * 100
    except:
        return None

# ---------------- 36-MONTH GROWTH (STAGE 2 HARD GATE) ----------------

def triangulate_36m_growth(sqm_36m, htag_36m, typical_36m):
    """
    Triangulate 36-month growth from SQM, HTAG, and Typical Value sources.

    Returns:
        {
            "sqm_36m": float or None,
            "htag_36m": float or None,
            "typical_36m": float or None,
            "avg_36m": float or None,
            "status": "PASS" | "FAIL" | "INSUFFICIENT_DATA"
        }
    """
    values = [
        v for v in [sqm_36m, htag_36m, typical_36m]
        if isinstance(v, (int, float))
    ]

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
# ---------------- 10-YEAR GROWTH (STAGE 2 SUSTAINABILITY GATE) ----------------

def triangulate_10y_growth(
    sqm_cagr,          # already p.a. from SQM
    oth_total_growth,  # TOTAL % growth (OTH)
    htag_total_growth  # TOTAL % growth (HTAG)
):
    """
    Triangulate 10-year growth using:
    - SQM CAGR (as-is)
    - OTH total -> CAGR
    - HTAG total -> CAGR
    """

    oth_cagr = calculate_cagr_from_total(oth_total_growth)
    htag_cagr = calculate_cagr_from_total(htag_total_growth)

    values = [
        v for v in [sqm_cagr, oth_cagr, htag_cagr]
        if isinstance(v, (int, float))
    ]

    if len(values) < 2:
        return {
            "sqm_cagr": sqm_cagr,
            "oth_cagr": oth_cagr,
            "htag_cagr": htag_cagr,
            "total_cagr": None,
            "alignment_gap": None,
            "status": "INSUFFICIENT_DATA",
        }

    total_cagr = sum(values) / len(values)

    # Alignment check: OTH vs Total CAGR
    alignment_gap = (
        abs(oth_cagr - total_cagr)
        if oth_cagr is not None
        else None
    )

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

   # ---------------- STAGE 3 – TEMP STRUCTURAL PLACEHOLDER ----------------

    # This will be replaced later by real ABS / planning / job data

    abs_data = get_abs_structural(row.get("Suburb"))

    structural_data = {
        # ---- Supply & others stay placeholders for now ----
        "approval_ratio_18m": 5.5,
        "developable_land": "LOW",
    
        # ✅ REAL ABS DATA
        "prof_occ_delta_2016": abs_data.get("prof_occ_delta_2016"),
        "prof_occ_delta_2021": abs_data.get("prof_occ_delta_2021"),
        "income_delta_2016": abs_data.get("income_delta_2016"),
        "income_delta_2021": abs_data.get("income_delta_2021"),
    
        # ---- still placeholders (next steps) ----
        "rent_stress_ok_pct": 67,
        "mortgage_stress_ok_pct": 78,
        "job_count": 620,
        "travel_time_mins": 42,
        "employment_diversity": "HIGH",
        "affordability_band": "GOOD",
    }

    
    structural_stage3 = evaluate_structural_score(structural_data)
      
    confidence_score, confidence_band = calculate_confidence(decision)
    investability_score = calculate_investability_score(
        confidence_score,
        structural_stage3["Final"]
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

        
    # ✅ NEW
        "Structural Stage 3": structural_stage3,

        "Narrative": narrative,
    }
# ============================================================
# STAGE 3 — STRUCTURAL SCORING (NO SCRAPING YET)
# ============================================================

def evaluate_structural_score(structural):
    """
    Evaluates suburb-level structural durability using Stage 3 rules.
    Returns BUY / WATCH / AVOID based on PASS / WARN / FAIL counts.
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

    # ---------- SUPPLY ----------
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

    # ---------- EMPLOYMENT QUALITY ----------
    for year in ["2016", "2021"]:
        delta = structural.get(f"prof_occ_delta_{year}")
        if delta is not None:
            if delta > 0:
                score(f"Professional Jobs {year}", "PASS")
            elif delta == 0:
                score(f"Professional Jobs {year}", "WARN")
            else:
                score(f"Professional Jobs {year}", "FAIL")

    # ---------- INCOME ----------
    for year in ["2016", "2021"]:
        delta = structural.get(f"income_delta_{year}")
        if delta is not None:
            if delta > 0:
                score(f"Income Growth {year}", "PASS")
            elif delta == 0:
                score(f"Income Growth {year}", "WARN")
            else:
                score(f"Income Growth {year}", "FAIL")

    # ---------- AFFORDABILITY / STRESS ----------
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

    # ---------- JOB INFRASTRUCTURE ----------
    jobs = structural.get("job_count")
    if jobs is not None:
        if jobs >= 500:
            score("Job Infrastructure", "PASS", critical=True)
        elif jobs >= 50:
            score("Job Infrastructure", "WARN", critical=True)
        else:
            score("Job Infrastructure", "FAIL", critical=True)

    # ---------- ACCESSIBILITY ----------
    travel = structural.get("travel_time_mins")
    if travel is not None:
        if travel < 45:
            score("Accessibility", "PASS")
        elif travel <= 60:
            score("Accessibility", "WARN")
        else:
            score("Accessibility", "FAIL")

    # ---------- ECONOMIC DIVERSITY ----------
    diversity = structural.get("employment_diversity")
    if diversity == "HIGH":
        score("Employment Diversity", "PASS")
    elif diversity == "MEDIUM":
        score("Employment Diversity", "WARN")
    elif diversity == "LOW":
        score("Employment Diversity", "FAIL")

    # ---------- HOUSING AFFORDABILITY ----------
    affordability = structural.get("affordability_band")
    if affordability == "GOOD":
        score("Housing Affordability", "PASS")
    elif affordability == "STRETCHED":
        score("Housing Affordability", "WARN")
    elif affordability == "SEVERE":
        score("Housing Affordability", "FAIL")

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
