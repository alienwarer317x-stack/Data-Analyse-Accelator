import requests
from bs4 import BeautifulSoup


# -------------------------------------------------
# Utility: Safe float parser
# -------------------------------------------------
def to_float(val):
    """
    Safely converts ABS values like '31.4%' into floats.
    Returns None on failure.
    """
    try:
        return float(
            str(val)
            .replace("%", "")
            .replace(",", "")
            .strip()
        )
    except Exception:
        return None


# -------------------------------------------------
# Utility: Safe HTTP fetcher
# -------------------------------------------------
def _fetch_abs_page(url):
    """
    Fetches an ABS QuickStats page safely.
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


# -------------------------------------------------
# ABS QuickStats URL builder
# -------------------------------------------------
def _build_quickstats_url(state, suburb):
    """
    Builds the ABS QuickStats URL for a suburb.

    Example:
      suburb = "Grafton", state = "NSW"
      -> https://www.abs.gov.au/census/find-census-data/quickstats/2021/GraftonNSW
    """
    suburb_code = f"{suburb.replace(' ', '')}{state.upper()}"
    return (
        "https://www.abs.gov.au/census/"
        "find-census-data/quickstats/2021/"
        f"{suburb_code}"
    )


# -------------------------------------------------
# Public fetcher: Renters percentage
# -------------------------------------------------
def fetch_renters_pct(state, suburb):
    """
    Fetches the percentage of households renting from
    ABS QuickStats (2021 Census).

    Returns:
      float (e.g. 31.4) or None
    """

    url = _build_quickstats_url(state, suburb)
    html = _fetch_abs_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # ABS tables use rows where labels like "Rented" appear
    rows = soup.find_all("tr")

    for row in rows:
        cells = row.find_all(["th", "td"])
        texts = [c.get_text(strip=True) for c in cells]

        # Look explicitly for the "Rented" tenure row
        if "Rented" in texts:
            for t in texts:
                if "%" in t:
                    return to_float(t)

    return None
