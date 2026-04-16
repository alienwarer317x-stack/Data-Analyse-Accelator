from ingestion.abs_adapter import fetch_renters_pct
import requests
from bs4 import BeautifulSoup


# -----------------------------
# Utility: Safe float parser
# -----------------------------
def to_float(val):
    """
    Safely converts SQM scraped values into floats.
    Examples:
      "0.73%"   -> 0.73
      "41 days" -> 41.0
      None      -> None
    """
    try:
        return float(
            str(val)
            .replace("%", "")
            .replace("days", "")
            .replace("day", "")
            .replace(",", "")
            .strip()
        )
    except Exception:
        return None


# -----------------------------
# Utility: Safe HTTP fetcher
# -----------------------------
def _fetch_sqm_page(url):
    """
    Fetches an SQM page safely.
    Returns HTML text or None on failure.
    """
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; MarketExplorer/1.0)"
            },
            timeout=15
        )
        if response.status_code != 200:
            return None
        return response.text
    except Exception:
        return None


# -----------------------------
# URL builders
# -----------------------------
def _build_vacancy_url(state, suburb):
    region = f"{state.upper()}-{suburb.replace(' ', '+')}"
    return f"https://sqmresearch.com.au/graph_vacancy_rate.php?region={region}"


def _build_stock_url(state, suburb):
    region = f"{state.upper()}-{suburb.replace(' ', '+')}"
    return f"https://sqmresearch.com.au/graph_stock_on_market.php?region={region}"


def _build_dom_url(state, suburb):
    region = f"{state.upper()}-{suburb.replace(' ', '+')}"
    return f"https://sqmresearch.com.au/graph_days_on_market.php?region={region}"


# -----------------------------
# Fetchers
# -----------------------------
def fetch_vacancy_rate(state, suburb):
    """
    Fetches the latest SQM vacancy rate (%) for a suburb.
    Returns a float (e.g. 0.73) or None.
    """
    html = _fetch_sqm_page(_build_vacancy_url(state, suburb))
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.find_all(string=lambda t: t and "%" in t)

    for text in candidates:
        value = to_float(text)
        # Vacancy rates are typically between 0% and 10%
        if value is not None and 0 <= value <= 10:
            return value

    return None


def fetch_stock_on_market(state, suburb):
    """
    Fetches the latest SQM percent stock on market for a suburb.
    Returns a float (e.g. 1.05) or None.
    """
    html = _fetch_sqm_page(_build_stock_url(state, suburb))
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.find_all(string=lambda t: t and "%" in t)

    for text in candidates:
        value = to_float(text)
        # Stock on market % is also typically low (<10%)
        if value is not None and 0 <= value <= 10:
            return value

    return None


def fetch_days_on_market(state, suburb):
    """
    Fetches the average days on market for a suburb.
    Returns a float (e.g. 39.0) or None.
    """
    html = _fetch_sqm_page(_build_dom_url(state, suburb))
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.find_all(
        string=lambda t: t and any(c.isdigit() for c in t)
    )

    for text in candidates:
        value = to_float(text)
        # Days on market should be a reasonable number
        if value is not None and 0 < value < 365:
            return value

    return None


# -----------------------------
# Public adapter function
# -----------------------------
def build_row_from_sqm(state, suburb):
    """
    Builds a _row dict for Explorer using live SQM data.
    This mirrors the DSR adapter but uses scraping instead.
    """

    return {
        "Vacancy rate": fetch_vacancy_rate(state, suburb),
        "Percent stock on market": fetch_stock_on_market(state, suburb),
        "Days on market": fetch_days_on_market(state, suburb),

        # Fields to be populated by later ingestion steps
        "Gross rental yield": None,
        "Percent renters in market": fetch_renters_pct(state, suburb),
        "Statistical reliability": None,

        # Context
        "State": state,
        "Suburb": suburb,
    }
