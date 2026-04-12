def clamp(value, lower=0.0, upper=1.0):
    return max(lower, min(value, upper))


def calculate_demand_supply_ratio(
    vacancy_pct: float,
    stock_on_market_pct: float,
    days_on_market: int,
    dom_long_term_avg: int,
    vacancy_upper_bound: float = 5.0,
    som_upper_bound: float = 2.5
) -> float:
    """
    Returns a Demand–Supply Ratio score between 0 and 100.

    All inputs must be non-negative and already normalised by ingestion.
    """

    # Defensive checks
    if (
        vacancy_pct is None or
        stock_on_market_pct is None or
        days_on_market is None or
        dom_long_term_avg is None or
        dom_long_term_avg <= 0
    ):
        return None  # upstream will handle confidence penalty

    # Vacancy (lower = better)
    vacancy_score = clamp(
        1 - (vacancy_pct / vacancy_upper_bound)
    )

    # Stock on market (lower = better)
    som_score = clamp(
        1 - (stock_on_market_pct / som_upper_bound)
    )

    # Days on market (relative measure)
    dom_ratio = days_on_market / dom_long_term_avg
    dom_score = clamp(
        1 - dom_ratio
    )

    # Weighted composite
    raw_score = (
        0.40 * vacancy_score +
        0.35 * som_score +
        0.25 * dom_score
    )

    return round(raw_score * 100, 1)
