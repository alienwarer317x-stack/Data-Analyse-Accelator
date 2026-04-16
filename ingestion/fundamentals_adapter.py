# ============================================================
# STRUCTURAL FUNDAMENTALS INGESTION ADAPTER
# ============================================================

"""
This adapter ingests slow-moving structural fundamentals.

Principles:
- No BUY / AVOID logic here
- No investment enforcement here
- Always degrades safely
- Never raises exceptions upstream
"""

# -----------------------------
# Utilities
# -----------------------------

def safe_bool(val):
    if isinstance(val, bool):
        return val
    return None


def safe_pct(val):
    try:
        return float(val)
    except Exception:
        return None


def safe_int(val):
    try:
        return int(val)
    except Exception:
        return None


# -----------------------------
# Supply Pipeline
# -----------------------------

def fetch_build_approvals_pct_18m(suburb):
    """
    % of total dwelling stock approved in last 18 months.
    Placeholder for ABS / planning datasets.
    """
    return None


def fetch_developable_land_supply(suburb):
    """
    Low / Medium / High
    """
    return None


# -----------------------------
# Employment Structure
# -----------------------------

def fetch_professional_growth_2016(suburb):
    """
    True if professional occupations grew faster than state average.
    """
    return None


def fetch_professional_growth_2021(suburb):
    return None


def fetch_industry_diversification(suburb):
    """
    True if employment is diversified.
    """
    return None


def fetch_job_infrastructure_count(suburb):
    """
    Count of major anchored job nodes.
    """
    return None


# -----------------------------
# Income & Affordability
# -----------------------------

def fetch_income_growth_2016(suburb):
    return None


def fetch_income_growth_2021(suburb):
    return None


def fetch_rent_stress_low_pct(suburb):
    """
    % households spending <30% of income on rent.
    """
    return None


def fetch_mortgage_stress_low_pct(suburb):
    """
    % owner-occupiers spending <30% of income on mortgage.
    """
    return None


def fetch_housing_affordability(suburb):
    """
    Good / Neutral / Poor
    """
    return None


# -----------------------------
# Accessibility
# -----------------------------

def fetch_average_travel_time(suburb):
    """
    Average commute time in minutes.
    """
    return None


# -----------------------------
# Public Structural Payload
# -----------------------------

def fetch_structural_fundamentals(suburb):
    """
    Canonical, slow-moving structural fundamentals payload.
    """

    return {
        # Supply
        "build_approvals_pct_18m": fetch_build_approvals_pct_18m(suburb),
        "developable_land_supply": fetch_developable_land_supply(suburb),

        # Employment
        "professional_growth_2016": safe_bool(fetch_professional_growth_2016(suburb)),
        "professional_growth_2021": safe_bool(fetch_professional_growth_2021(suburb)),
        "industry_diversification": safe_bool(fetch_industry_diversification(suburb)),
        "job_infrastructure_count": safe_int(fetch_job_infrastructure_count(suburb)),

        # Income & affordability
        "income_growth_2016": safe_bool(fetch_income_growth_2016(suburb)),
        "income_growth_2021": safe_bool(fetch_income_growth_2021(suburb)),
        "rent_stress_low_pct": safe_pct(fetch_rent_stress_low_pct(suburb)),
        "mortgage_stress_low_pct": safe_pct(fetch_mortgage_stress_low_pct(suburb)),
        "housing_affordability": fetch_housing_affordability(suburb),

        # Accessibility
        "average_travel_time": safe_int(fetch_average_travel_time(suburb)),
    }


# Backward-compatible alias expected by engine
def get_structural_fundamentals(suburb):
    return fetch_structural_fundamentals(suburb)


# -----------------------------
# Structural Evaluation
# -----------------------------

def evaluate_structural_gates(f):
    """
    Evaluates long-term structural fundamentals.

    Returns:
    {
        "status": "PASS" | "WARN" | "FAIL" | "EXCELLENT",
        "failed": [...],
        "warnings": [...]
    }
    """

    if not isinstance(f, dict):
        return {
            "status": "WARN",
            "failed": [],
            "warnings": ["Structural data unavailable"],
        }

    failed = []
    warnings = []
    excellence = []

    # ---------------- Supply ----------------
    approvals = f.get("build_approvals_pct_18m")
    if approvals is not None:
        if approvals > 8:
            failed.append("High supply pipeline")
        elif approvals >= 6:
            warnings.append("Elevated supply pipeline")

    land = f.get("developable_land_supply")
    if land == "High":
        failed.append("High developable land availability")
    elif land == "Medium":
        warnings.append("Moderate land availability")

    # ---------------- Employment ----------------
    prof_16 = f.get("professional_growth_2016")
    prof_21 = f.get("professional_growth_2021")

    if prof_16 is False and prof_21 is False:
        failed.append("Weak professional employment growth")
    elif prof_16 is False or prof_21 is False:
        warnings.append("Mixed professional employment growth")
    elif prof_16 and prof_21:
        excellence.append("Strong professional employment growth")

    diversified = f.get("industry_diversification")
    if diversified is False:
        failed.append("Undiversified employment base")
    elif diversified is None:
        warnings.append("Employment diversification unknown")

    jobs = f.get("job_infrastructure_count")
    if jobs is not None:
        if jobs < 75:
            failed.append("Insufficient local job infrastructure")
        elif jobs >= 500:
            excellence.append("Strong anchored employment base")
        else:
            warnings.append("Moderate job infrastructure")

    # ---------------- Income ----------------
    inc_16 = f.get("income_growth_2016")
    inc_21 = f.get("income_growth_2021")

    if inc_16 is False and inc_21 is False:
        failed.append("Weak household income growth")
    elif inc_16 is False or inc_21 is False:
        warnings.append("Mixed income growth performance")
    elif inc_16 and inc_21:
        excellence.append("Household incomes outperformed state")

    rent_ok = f.get("rent_stress_low_pct")
    if rent_ok is not None:
        if rent_ok < 50:
            failed.append("High rental stress")
        elif rent_ok < 60:
            warnings.append("Moderate rental stress")

    mortgage_ok = f.get("mortgage_stress_low_pct")
    if mortgage_ok is not None:
        if mortgage_ok < 65:
            failed.append("High mortgage stress")
        elif mortgage_ok < 75:
            warnings.append("Moderate mortgage stress")

    affordability = f.get("housing_affordability")
    if affordability == "Poor":
        failed.append("Poor housing affordability")
    elif affordability == "Neutral":
        warnings.append("Affordability tightening")

    # ---------------- Accessibility ----------------
    travel = f.get("average_travel_time")
    if travel is not None:
        if travel > 75:
            failed.append("Excessive commute times")
        elif travel > 45:
            warnings.append("Long commute times")

    # ---------------- Final Status ----------------
    if failed:
        status = "FAIL"
    elif len(warnings) >= 2:
        status = "WARN"
    elif excellence:
        status = "EXCELLENT"
    else:
        status = "PASS"

    return {
        "status": status,
        "failed": failed,
        "warnings": warnings,
    }
