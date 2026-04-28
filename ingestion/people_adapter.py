import pandas as pd
import os

_PEOPLE = None
PATH = os.path.join("data", "abs_people.csv")

if os.path.exists(PATH):
    try:
        _PEOPLE = pd.read_csv(PATH)
    except Exception:
        _PEOPLE = None


def get_people_profile(suburb, state=None, post code=None):
    """
    Returns ABS-based demographic metrics for a suburb.
    Fails safely if data not found.
    """
    if _PEOPLE is None or not suburb:
        return {}

    df = _PEOPLE[
    _PEOPLE["Suburb"]
    .astype(str)
    .str.upper()
    .str.strip()
    == suburb.upper().strip()
    ]

    if state and "State" in df.columns:
        df = df[df["State"] == state]

    if postcode and "Postcode" in df.columns:
    try:
        df_postcode = df[df["Postcode"].astype(str) == str(int(postcode))]
        if not df_postcode.empty:
            df = df_postcode
    except Exception:
        pass

    if df.empty:
        return {}

    r = df.iloc[0]

    return {
        "population": r.get("Population"),
        "population_growth_pct": r.get("Population_Growth_Pct"),
        "median_age": r.get("Median_Age"),
        "household_size": r.get("Household_Size"),
        "renters_pct": r.get("Renters_Pct"),
        "owners_pct": r.get("Owners_Pct"),
        "families_pct": r.get("Families_Pct"),
        "source": "ABS Census"
    }
