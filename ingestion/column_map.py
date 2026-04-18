# ingestion/column_map.py
import re
from typing import Optional

# canonical names used by engine and validator
CANONICAL = {
    "vacancy_rate": "Vacancy rate",
    "percent_stock_on_market": "Percent stock on market",
    "days_on_market": "Days on market",
    "gross_rental_yield": "Gross rental yield",
    "percent_renters_in_market": "Percent renters in market",
    "statistical_reliability": "Statistical reliability",
    # add the rest used by engine
    "median_price": "Median price",
    "population_growth": "Population growth",
    "household_income": "Household income",
    "sales_volume": "Sales volume",
    # ... extend as needed
}

# common variants mapped to canonical keys
VARIANTS = {
    "vacancy": "vacancy_rate",
    "vacancy rate": "vacancy_rate",
    "vacancy%": "vacancy_rate",
    "percent stock": "percent_stock_on_market",
    "stock on market": "percent_stock_on_market",
    "days on market": "days_on_market",
    "dom": "days_on_market",
    "gross rental yield": "gross_rental_yield",
    "rental yield": "gross_rental_yield",
    "percent renters": "percent_renters_in_market",
    "statistical reliability": "statistical_reliability",
    "median price": "median_price",
    "median": "median_price",
    "population growth": "population_growth",
    "pop growth": "population_growth",
    "household income": "household_income",
    "sales volume": "sales_volume",
}

def normalise_heading(h: str) -> Optional[str]:
    if not h or not isinstance(h, str):
        return None
    key = h.strip().lower()
    key = re.sub(r"[^a-z0-9 ]", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    # direct variant match
    if key in VARIANTS:
        return CANONICAL[VARIANTS[key]]
    # try exact canonical match
    for canon in CANONICAL.values():
        if canon.lower() == key:
            return canon
    # fuzzy heuristics
    if "vacancy" in key:
        return CANONICAL["vacancy_rate"]
    if "yield" in key and "rental" in key:
        return CANONICAL["gross_rental_yield"]
    if "median" in key and "price" in key:
        return CANONICAL["median_price"]
    return None
