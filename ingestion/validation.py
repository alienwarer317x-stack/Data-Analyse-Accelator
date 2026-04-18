# top of ingestion/validation.py
from .column_map import normalise_heading, CANONICAL
# after df is loaded
def _canonicalise_df(df):
    mapping = {}
    for col in df.columns:
        canon = normalise_heading(col)
        if canon:
            mapping[col] = canon
    # rename only mapped columns
    return df.rename(columns=mapping), mapping

def validate_dsr_dataframe(df: pd.DataFrame):
    df, mapping = _canonicalise_df(df)
    # now use df with canonical names
    # update REQUIRED lists to use CANONICAL values
    REQUIRED_NUMERIC = [
        "Vacancy rate",
        "Percent stock on market",
        "Days on market",
        "Gross rental yield",
        "Percent renters in market",
        "Statistical reliability",
        # add new required fields used by engine
        "Median price",
        "Population growth",
    ]
    # rest of your existing validation logic unchanged but using canonical names
