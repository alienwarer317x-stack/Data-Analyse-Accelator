# ingestion/abs_adapter.py

import pandas as pd

# ------------------------------------------------------------------
# Load ABS-derived suburb-level metrics from local CSV (no scraping)
# ------------------------------------------------------------------

ABS_DATA_PATH = "data/abs_structural.csv"

def load_abs_data():
    """
    Expected columns:
    Suburb
    prof_occ_delta_2016
    prof_occ_delta_2021
    income_delta_2016
    income_delta_2021
    """
    return pd.read_csv(ABS_DATA_PATH)


def get_abs_structural(suburb_name):
    df = load_abs_data()

    row = df[df["Suburb"].str.upper() == suburb_name.upper()]
    if row.empty:
        return {}

    r = row.iloc[0]

    return {
        "prof_occ_delta_2016": r.get("prof_occ_delta_2016"),
        "prof_occ_delta_2021": r.get("prof_occ_delta_2021"),
        "income_delta_2016": r.get("income_delta_2016"),
        "income_delta_2021": r.get("income_delta_2021"),
    }
