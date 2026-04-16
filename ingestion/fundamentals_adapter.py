# ============================================================
# STRUCTURAL FUNDAMENTALS INGESTION ADAPTER
# ============================================================

"""
This adapter ingests slow-moving structural fundamentals.

Rules:
- No BUY / AVOID logic here
- No thresholds enforced here
- Degrades safely (returns None if data unavailable)
"""

import math


# -----------------------------
# Utilities
# -----------------------------

def safe_bool(val):
    if val is None:
        return None
    return bool(val)


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
    Placeholder: should be fed from ABS 8731.0 / planning datasets.
    """
    # TODO: Replace with ABS Building Approvals ingestion
    return None


def fetch_developable_land_supply(suburb):
    """
    Categorical land supply assessment.
    Low / Medium / High
    """
    # TODO: Replace with state planning datasets
    return None


# -----------------------------
# Employment Structure
# -----------------------------

def fetch_professional_growth_2016(suburb):
    """
    True if professional occupations grew faster than state average (2011–2016).
    ABS Census derived.
    """
    return None


def fetch_professional_growth_2021(suburb):
    """
    True if professional occupations grew faster than state average (2016–2021).
    ABS Census derived.
    """
    return None


def fetch_industry_diversification(suburb):
    """
    True if no single industry dominates employment.
    """
    return None


def fetch_job_infrastructure_count(suburb):
    """
    Count of major employment nodes (hospitals, universities, logistics).
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
    % households spending <30% of income on mortgage.
    """
    return None


def fetch_housing_affordability(suburb):
    """
    Good / Neutral / Poor affordability.
    """
    return None


# -----------------------------
# Accessibility
# -----------------------------

def fetch_average_travel_time(suburb):
    """
    Average commute / accessibility time in minutes.
    """
    return None


# -----------------------------
# Public Entry Point
# -----------------------------

def fetch_structural_fundamentals(suburb):
    """
    Canonical structural fundamentals payload.
    """

    return {
        # Supply
        "build_approvals_pct_18m": fetch_build_approvals_pct_18m(suburb),
        "developable_land_supply": fetch_developable_land_supply(suburb),

        # Employment
        "professional_growth_2016": fetch_professional_growth_2016(suburb),
        "professional_growth_2021": fetch_professional_growth_2021(suburb),
        "industry_diversification": fetch_industry_diversification(suburb),
        "job_infrastructure_count": fetch_job_infrastructure_count(suburb),

        # Income & affordability
        "income_growth_2016": fetch_income_growth_2016(suburb),
        "income_growth_2021": fetch_income_growth_2021(suburb),
        "rent_stress_low_pct": fetch_rent_stress_low_pct(suburb),
        "mortgage_stress_low_pct": fetch_mortgage_stress_low_pct(suburb),
        "housing_affordability": fetch_housing_affordability(suburb),

        # Accessibility
        "average_travel_time": fetch_average_travel_time(suburb),
    }
