import pandas as pd

_LOOKUP = pd.read_csv("data/suburb_lookup.csv")

def lookup_suburb(suburb, state=None):
    df = _LOOKUP[_LOOKUP["Suburb"].str.upper() == suburb.upper()]
    if state:
        df = df[df["State"] == state]
    if df.empty:
        return {}
    return df.iloc[0].to_dict()
