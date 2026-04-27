import pandas as pd
import os

_LOOKUP = None

LOOKUP_PATH = os.path.join("data", "suburb_lookup.csv")

if os.path.exists(LOOKUP_PATH):
    try:
        _LOOKUP = pd.read_csv(LOOKUP_PATH)
    except Exception:
        _LOOKUP = None
else:
    _LOOKUP = None


def lookup_suburb(suburb, state=None):
    """
    Safe suburb lookup.
    Returns {} if lookup data is unavailable.
    """
    if _LOOKUP is None or not suburb:
        return {}

    df = _LOOKUP[_LOOKUP["Suburb"].str.upper() == suburb.upper()]

    if state and "State" in df.columns:
        df = df[df["State"] == state]

    if df.empty:
        return {}

    return df.iloc[0].to_dict()
