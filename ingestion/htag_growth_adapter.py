# ingestion/htag_growth_adapter.py
import time
import json
import hashlib
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup
from pathlib import Path

CACHE_DIR = Path(".cache/htag_growth")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
USER_AGENT = "Data-Analyse-Accelerator/1.0 (+https://example.local)"

def _cache_path_for_url(url: str) -> Path:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{h}.json"

def _save_cache(url: str, data: Dict):
    p = _cache_path_for_url(url)
    with p.open("w", encoding="utf-8") as f:
        json.dump({"fetched_at": time.time(), "data": data}, f)

def _load_cache(url: str, max_age_seconds: int = 60 * 60 * 24) -> Optional[Dict]:
    p = _cache_path_for_url(url)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if time.time() - payload.get("fetched_at", 0) > max_age_seconds:
            return None
        return payload.get("data")
    except Exception:
        return None

def fetch_htag_growth(url: str, use_cache: bool = True, max_retries: int = 3, backoff: float = 0.5) -> Dict:
    """
    Fetch and parse hashtag growth or similar metrics from a target URL.
    Returns a dict with structured fields. Always returns a dict; on error returns {'error': '...'}.
    """
    if use_cache:
        cached = _load_cache(url)
        if cached is not None:
            return {"from_cache": True, "payload": cached}

    headers = {"User-Agent": USER_AGENT}
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "lxml")
            # Example parsing heuristics. Adapt selectors to the real site.
            result = {}
            # find numeric badges
            for label in soup.select(".metric, .stat, .badge"):
                text = label.get_text(" ", strip=True)
                if not text:
                    continue
                # naive split "Followers 12.3k"
                parts = text.split()
                if len(parts) >= 2 and parts[-1].replace(",", "").replace(".", "").isdigit():
                    key = " ".join(parts[:-1])
                    val = parts[-1]
                    result[key] = val
            # fallback: parse tables
            for table in soup.find_all("table"):
                headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
                if not headers:
                    # try first row as header
                    first_row = table.find("tr")
                    if first_row:
                        headers = [td.get_text(" ", strip=True) for td in first_row.find_all(["td","th"])]
                rows = []
                for tr in table.select("tbody tr"):
                    cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td","th"])]
                    if cells:
                        rows.append(cells)
                if headers and rows:
                    result.setdefault("tables", []).append({"headers": headers, "rows": rows})
            # Save and return
            _save_cache(url, result)
            return {"from_cache": False, "payload": result}
        except Exception as exc:
            last_exc = exc
            time.sleep(backoff * attempt)
            continue
    return {"error": f"failed to fetch {url}: {last_exc}"}
