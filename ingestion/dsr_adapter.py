def to_float(val):
    """
    Safely converts DSR spreadsheet values into floats.
    Examples:
      "0.73%"   -> 0.73
      "45 days" -> 45.0
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


def build_row_from_dsr(r):
    """
    Converts one DSR Excel row into a clean _row dict
    that matches the locked engine contract.
    """

    return {
        # === REQUIRED BY ENGINE ===
        "Vacancy rate": to_float(r.get("Vacancy rate")),
        "Percent stock on market": to_float(r.get("Percent stock on market")),
        "Days on market": to_float(r.get("Days on market")),
        "Gross rental yield": to_float(r.get("Gross rental yield")),
        "Percent renters in market": to_float(r.get("Percent renters in market")),
        "Statistical reliability": to_float(r.get("Statistical reliability")),

        # === CONTEXT (SAFE, NOT USED BY LOGIC) ===
        "State": r.get("State"),
        "Suburb": r.get("Suburb"),
        "Post Code": r.get("Post Code"),
        "Median Price": to_float(
            r.get("Median 12 months") or r.get("Typical value")
        ),
    }
