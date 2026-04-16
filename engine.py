# ============================================================
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
    # ============================================================
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
# ---------------- STRUCTURAL FUNDAMENTALS GATES ----------------

def evaluate_structural_gates(f):
    """
    Evaluates long-term structural fundamentals.
    Returns:
      {
        "status": "PASS" | "WARN" | "FAIL" | "EXCELLENT",
        "failed": [reasons],
        "warnings": [reasons]
      }
    """

    failed = []
    warnings = []
    excellence_flags = []

    # --------------------------------------------------
    # SUPPLY PIPELINE
    # --------------------------------------------------

    # 18-month building approvals vs total dwellings
    approvals = f.get("build_approvals_pct_18m")
    if approvals is not None:
        if approvals > 8:
            failed.append("High supply pipeline (building approvals exceed 8% of dwelling stock)")
        elif approvals >= 6:
            warnings.append("Elevated supply pipeline (building approvals are rising)")

    # Developable land supply
    land_supply = f.get("developable_land_supply")
    if land_supply == "High":
        failed.append("High developable land supply creates long-term price ceiling")
    elif land_supply == "Medium":
        warnings.append("Moderate land availability; future supply should be monitored")

    # --------------------------------------------------
    # EMPLOYMENT STRUCTURE
    # --------------------------------------------------

    # Professional occupations growth (2016 & 2021)
    prof_2016 = f.get("professional_growth_2016")
    prof_2021 = f.get("professional_growth_2021")

    if prof_2016 is False and prof_2021 is False:
        failed.append("Professional employment growth lags state benchmarks")
    elif prof_2016 is False or prof_2021 is False:
        warnings.append("Mixed professional employment growth across census cycles")
    elif prof_2016 is True and prof_2021 is True:
        excellence_flags.append("Strong professional employment growth across cycles")

    # Industry diversification
    diversified = f.get("industry_diversification")
    if diversified is False:
        failed.append("Employment base lacks industry diversification")
    elif diversified is None:
        warnings.append("Employment diversification could not be confirmed")

    # Job infrastructure (aggregated qualifying jobs)
    jobs = f.get("job_infrastructure_count")
    if jobs is not None:
        if jobs < 75:
            failed.append("Insufficient local job infrastructure (<75 anchored jobs)")
        elif jobs >= 500:
            excellence_flags.append("Strong anchored employment base (≥500 jobs)")
        else:
            # 75–499 jobs
            warnings.append("Moderate local employment base; reliance on external job markets")

    # --------------------------------------------------
    # INCOME & AFFORDABILITY
    # --------------------------------------------------

    income_2016 = f.get("income_growth_2016")
    income_2021 = f.get("income_growth_2021")

    if income_2016 is False and income_2021 is False:
        failed.append("Household income growth lags state benchmarks")
    elif income_2016 is False or income_2021 is False:
        warnings.append("Household income growth has been mixed relative to state")
    elif income_2016 is True and income_2021 is True:
        excellence_flags.append("Household income growth outpaced state benchmarks")

    rent_ok = f.get("rent_stress_low_pct")
    if rent_ok is not None:
        if rent_ok < 50:
            failed.append("High rental stress across households")
        elif rent_ok < 60:
            warnings.append("Moderate rental stress levels")

    mortgage_ok = f.get("mortgage_stress_low_pct")
    if mortgage_ok is not None:
        if mortgage_ok < 65:
            failed.append("High mortgage stress across owner-occupiers")
        elif mortgage_ok < 75:
            warnings.append("Moderate mortgage stress levels")

    affordability = f.get("housing_affordability")
    if affordability == "Poor":
        failed.append("Structural housing affordability is poor")
    elif affordability == "Neutral":
        warnings.append("Housing affordability is tightening")

    # --------------------------------------------------
    # ACCESSIBILITY
    # --------------------------------------------------

    travel = f.get("average_travel_time")
    if travel is not None:
        if travel > 75:
            failed.append("Excessive travel times reduce long-term attractiveness")
        elif travel > 45:
            warnings.append("Longer commute times may limit demand depth")

    # --------------------------------------------------
    # FINAL STRUCTURAL STATUS
    # --------------------------------------------------

    if failed:
        status = "FAIL"
    elif len(warnings) >= 2:
        status = "WARN"
    elif excellence_flags:
        status = "EXCELLENT"
    else:
        status = "PASS"

    return {
        "status": status,
        "failed": failed,
        "warnings": warnings,
    }


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

    narrative = build_narrative(
        row=row,
        decision=decision,
        growth=growth,
        demand_supply=demand_supply
    )

    return {
        "Decision": decision,
        "Confidence": confidence_band,
        "Confidence Score": confidence_score,
        "Demand / Supply Ratio": demand_supply,
        "Market Cycle": classify_market_cycle(demand_supply),
        "Failed Gates": failed if failed else ["None"],
        "Growth": growth,
        "Narrative": narrative,
    }
