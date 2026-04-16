import requests
from bs4 import BeautifulSoup


def to_float(val):
    try:
        return float(
            str(val)
            .replace("%", "")
            .replace("days", "")
            .replace("day", "")
            .replace(",", "")
            .strip()
        )
    except:
        return None


def _fetch_sqm_page(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MarketExplorer/1.0)"},
            timeout=15
        )
        if response.status_code != 200:
            return None
        return response.text
    except:
        return None


def _build_vacancy_url(state, suburb):
    region = f"{state.upper()}-{suburb.replace(' ', '+')}"
    return f"https://sqmresearch.com.au/graph_vacancy_rate.php?region={region}"


def fetch_vacancy_rate(state, suburb):
    url = _build_vacancy_url(state, suburb)
    html = _fetch_sqm_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.find_all(string=lambda t: t and "%" in t)

    for text in candidates:
        value = to_float(text)
        if value is not None and 0 <= value <= 10:
            return value

    return None

def build_row_from_sqm(state, suburb):
    """
    Builds a _row dict for Explorer using live SQM data.
    This mirrors the DSR adapter but uses scraping instead.
    """

    return {
        "Vacancy rate": fetch_vacancy_rate(state, suburb),
        "Percent stock on market": fetch_stock_on_market(state, suburb),
        "Days on market": fetch_days_on_market(state, suburb),

        # Fields not available from SQM yet (populate later)
        "Gross rental yield": None,
        "Percent renters in market": None,
        "Statistical reliability": None,

        # Context
        "State": state,
        "Suburb": suburb,
    }
