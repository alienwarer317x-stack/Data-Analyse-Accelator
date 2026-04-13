def to_float(val):
    """
    Safely converts messy spreadsheet values into floats.
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


def build_row_from_dsr(r):
    """
    Converts one DSR Excel row into a clean _row dict
    that matches the locked engine contract.
    """

    return {
        # === REQUIRED BY ENGINE ===
        "Vacancy rate": to_float(
            r.get("Vacancy rate") or r.get("Vacancy Rate")
        ),

        "Percent stock on market": to_float(
            r.get("Percent stock on market") or r.get("Stock on market")
        ),

        "Days on market": to_float(
            r.get("Days on market") or r.get("Days on Market")
        ),

        "Gross rental yield": to_float(
            r.get("Gross rental yield") or r.get("Gross Yield")
        ),

        "Percent renters in market": to_float(
            r.get("Percent renters in market") or r.get("Renters %")
        ),

        "Statistical reliability": to_float(
            r.get("Statistical reliability") or r.get("Reliability")
        ),

        # === SAFE CONTEXT (NOT USED BY ENGINE) ===
        "State": r.get("State"),
        "Suburb": r.get("Suburb"),
        "Post Code": r.get("Post Code"),
        "Median Price": to_float(
            r.get("Median 12 months") or r.get("Typical value")
        ),
    }
