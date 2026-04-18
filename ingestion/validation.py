import pandas as pd
from .dsr_adapter import to_float

REQUIRED_NUMERIC = [
    "Vacancy rate",
    "Percent stock on market",
    "Days on market",
    "Gross rental yield",
    "Percent renters in market",
    "Statistical reliability",
]

REQUIRED_ANY = [
    "State",
    "Suburb",
]

def _has_column(df, col):
    return col in df.columns

def _column_has_numeric_values(df, col):
    if col not in df.columns:
        return False
    parsed = df[col].apply(lambda v: to_float(v))
    return parsed.notna().any()

def validate_dsr_dataframe(df: pd.DataFrame):
    errors = []
    warnings = []

    missing = [c for c in REQUIRED_NUMERIC + REQUIRED_ANY if not _has_column(df, c)]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return False, errors, warnings

    numeric_empty = [c for c in REQUIRED_NUMERIC if not _column_has_numeric_values(df, c)]
    if numeric_empty:
        errors.append(f"No parseable numeric values found in: {', '.join(numeric_empty)}")
        return False, errors, warnings

    row_warnings = []
    for i, row in df.iterrows():
        missing_count = 0
        for c in REQUIRED_NUMERIC:
            if to_float(row.get(c)) is None:
                missing_count += 1
        if missing_count >= max(1, len(REQUIRED_NUMERIC) // 2):
            row_warnings.append(f"Row {i+1} ({row.get('Suburb') or 'unknown suburb'}) has {missing_count} missing numeric fields")
    if row_warnings:
        warnings.extend(row_warnings)

    return True, errors, warnings

def format_errors(errors, warnings):
    lines = []
    if errors:
        lines.append("Errors:")
        lines.extend([f"- {e}" for e in errors])
    if warnings:
        lines.append("Warnings:")
        lines.extend([f"- {w}" for w in warnings])
    return "\n".join(lines)
