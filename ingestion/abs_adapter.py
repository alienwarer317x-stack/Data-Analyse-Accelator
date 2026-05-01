import pandas as pd

# ------------------------------------------------------------------
# ABS Structural Data Adapter
# Loads preprocessed ABS Census data from local CSV
# ------------------------------------------------------------------

ABS_DATA_PATH = "data/abs_structural.csv"


def load_abs_data():
    """Load ABS structural data from CSV"""
    try:
        return pd.read_csv(ABS_DATA_PATH)
    except FileNotFoundError:
        print(f"Warning: ABS data file not found at {ABS_DATA_PATH}")
        return pd.DataFrame()


def get_abs_structural(suburb_name):
    """
    Returns structural metrics for a given suburb.
    Returns empty dict if suburb not found.
    """
    if not suburb_name:
        return {}

    df = load_abs_data()
    if df.empty:
        return {}

    # Case-insensitive search
    suburb_upper = str(suburb_name).strip().upper()
    row = df[df["Suburb"].astype(str).str.upper() == suburb_upper]

    if row.empty:
        return {}

    r = row.iloc[0]

    return {
        "prof_occ_delta_2016": r.get("prof_occ_delta_2016"),
        "prof_occ_delta_2021": r.get("prof_occ_delta_2021"),
        "income_delta_2016": r.get("income_delta_2016"),
        "income_delta_2021": r.get("income_delta_2021"),
        "rent_stress_ok_pct": r.get("rent_stress_ok_pct"),
        "mortgage_stress_ok_pct": r.get("mortgage_stress_ok_pct"),
    }
