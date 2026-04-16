import requests
from bs4 import BeautifulSoup


# -----------------------------
# Utility: Safe float parser
# -----------------------------
def to_float(val):
    try:
        return float(
            str(val)
            .replace("%", "")
            .replace(",", "")
            .strip()
        )
    except Exception:
        return None


# -----------------------------
# Utility: Safe HTTP fetcher
# -----------------------------
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
    except Exception:
        return None


# -----------------------------
# URL builders (Growth)
# -----------------------------
def _build_3y_growth_url(state, suburb):
    region = f"{state.upper()}-{suburb.replace(' ', '+')}"
    return f"https://sqmresearch.com.au/graph_median_growth.php?region={region}&period=36"


def _build_10y_growth_url(state, suburb):
    region = f"{state.upper()}-{suburb.replace(' ', '+')}"
    return f"https://sqmresearch.com.au/graph_median_growth.php?region={region}&period=120"


# -----------------------------
# Fetchers
# -----------------------------
def fetch_3y_growth_pct(state, suburb):
    html = _fetch_sqm_page(_build_3y_growth_url(state, suburb))
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.find_all(string=lambda t: t and "%" in t)

    for text in candidates:
        value = to_float(text)
        if value is not None and 0 <= value <= 100:
            return value

    return None


def fetch_10y_growth_pct(state, suburb):
    html = _fetch_sqm_page(_build_10y_growth_url(state, suburb))
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.find_all(string=lambda t: t and "%" in t)

    for text in candidates:
        value = to_float(text)
        if value is not None and 0 <= value <= 200:
            return value

    return None


# -----------------------------
# Public adapter
# -----------------------------
def fetch_sqm_growth(state, suburb):
    return {
        "sqm_36m_growth_pct": fetch_3y_growth_pct(state, suburb),
        "sqm_10y_growth_pct": fetch_10y_growth_pct(state, suburb),
    }
