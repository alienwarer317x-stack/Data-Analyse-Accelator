# ingestion/structural_adapter.py

from ingestion.abs_adapter import get_abs_structural

# -------------------------------------------------------------------
# Stage 3 Structural Input Assembly
# -------------------------------------------------------------------
# This file ONLY assembles inputs.
# It does NOT score.
# It does NOT decide.
# -------------------------------------------------------------------

def get_structural_inputs(suburb):
    """
    Returns a unified structural input dictionary
    for Stage 3 evaluation.

    All values may be None if data is unavailable.
    """

    abs_data = get_abs_structural(suburb)

    return {
        # --- SUPPLY (to be wired later) ---
        "approval_ratio_18m": None,
        "developable_land": None,

        # --- EMPLOYMENT & INCOME (ABS) ---
        "prof_occ_delta_2016": abs_data.get("prof_occ_delta_2016"),
        "prof_occ_delta_2021": abs_data.get("prof_occ_delta_2021"),
        "income_delta_2016": abs_data.get("income_delta_2016"),
        "income_delta_2021": abs_data.get("income_delta_2021"),

        # --- STRESS / AFFORDABILITY (ABS) ---
        "rent_stress_ok_pct": abs_data.get("rent_stress_ok_pct"),
        "mortgage_stress_ok_pct": abs_data.get("mortgage_stress_ok_pct"),

        # --- JOBS (to be wired next) ---
        "job_count": None,

        # --- ACCESS & DIVERSITY (future) ---
        "travel_time_mins": None,
        "employment_diversity": None,
        "affordability_band": None,
    }
