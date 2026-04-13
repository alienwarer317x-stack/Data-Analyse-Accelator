import requests
from bs4 import BeautifulSoup


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
    except:
        return None
