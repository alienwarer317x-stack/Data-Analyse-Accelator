
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
def _fetch_oth_page(url):
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
# URL builders (OTH Growth)
# -----------------------------
def _build_oth_growth_url(state, suburb):
    suburb_slug = suburb.lower().replace(" ", "-")
    state_slug = state.lower()
    return f"https://www.onthehouse.com.au/suburb/{state_slug}/{suburb_slug}"


# -----------------------------
# Fetchers
# -----------------------------
def fetch_oth_10y_growth_pct(state, suburb):
    html = _fetch_oth_page(_build_oth_growth_url(state, suburb))
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
def fetch_oth_growth(state, suburb):
    return {
        "oth_10y_growth_pct": fetch_oth_10y_growth_pct(state, suburb)
    }
