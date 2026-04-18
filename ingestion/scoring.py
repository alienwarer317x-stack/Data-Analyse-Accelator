# ingestion/scoring.py
from typing import Dict, Tuple
from .dsr_adapter import to_float

WEIGHTS = {
    "Vacancy rate": -1.5,
    "Percent stock on market": -1.0,
    "Days on market": -0.5,
    "Gross rental yield": 2.0,
    "Percent renters in market": 0.5,
    "Statistical reliability": 1.0,
    "Median price": -0.3,
    "Population growth": 1.5,
}

def score_row(row: Dict) -> Tuple[float, str]:
    score = 0.0
    total_weight = 0.0
    for col, w in WEIGHTS.items():
        val = to_float(row.get(col))
        if val is None:
            continue
        score += w * val
        total_weight += abs(w)
    # normalise to 0-100 for UI
    if total_weight:
        norm = (score / total_weight)
    else:
        norm = 0.0
    # map to 0-100
    ui_score = max(0, min(100, 50 + norm))
    # decision label
    if ui_score >= 70:
        label = "Strong Buy"
    elif ui_score >= 55:
        label = "Buy"
    elif ui_score >= 45:
        label = "Hold"
    else:
        label = "Avoid"
    return ui_score, label
