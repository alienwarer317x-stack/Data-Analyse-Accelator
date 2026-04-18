# ingestion/sqm_adapter.py
from .htag_growth_adapter import fetch_htag_growth
from .dsr_adapter import to_float

def build_row_from_sqm(sqm_source: Dict) -> Dict:
    """
    sqm_source is expected to contain at least 'url' and 'suburb' keys.
    Returns a dict with canonical column names where possible.
    """
    url = sqm_source.get("url")
    suburb = sqm_source.get("suburb")
    row = {"Suburb": suburb}
    if not url:
        row["scrape_error"] = "no url provided"
        return row
    scraped = fetch_htag_growth(url)
    if "error" in scraped:
        row["scrape_error"] = scraped["error"]
        return row
    payload = scraped.get("payload", {})
    # Example mapping heuristics. Extend to match real site fields.
    # If payload contains tables, try to extract known keys
    if "tables" in payload:
        for table in payload["tables"]:
            for h, r in zip(table["headers"], table["rows"][0] if table["rows"] else []):
                # naive mapping
                if "vacancy" in h.lower():
                    row["Vacancy rate"] = r
                if "median" in h.lower() and "price" in h.lower():
                    row["Median price"] = r
    # merge any top-level metrics
    for k, v in payload.items():
        if isinstance(v, str):
            if "vacancy" in k.lower():
                row["Vacancy rate"] = v
            if "yield" in k.lower():
                row["Gross rental yield"] = v
    return row
