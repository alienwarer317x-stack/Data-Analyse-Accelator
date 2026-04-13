def to_float(val):
    """
    Safely converts messy spreadsheet values into floats.
    Examples:
      "45 days" -> 45.0
      "5.3%"    -> 5.3
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
    matching the locked data contract.
    """

    return {
        # === REQUIRED CORE FIELDS (ENGINE CONTRACT) ===
        "Vacancy rate": to_float(r.get("Vacancy rate")),
        "Percent stock on market": to_float(r.get("Percent stock on market")),
        
"Days on market": to_float(
    r.get("Days on market") or r.get("Days on Market")
),

        "Gross rental yield": to_float(r.get("Gross rental yield")),
        "Percent renters in market": to_float(r.get("Percent renters in market")),
        "Statistical reliability": to_float(r.get("Statistical reliability")),

        # === CONTEXT (OPTIONAL BUT USEFUL) ===
        "State": r.get("State"),
        "Suburb": r.get("Suburb"),
        "Post Code": r.get("Post Code"),
        "Median Price": to_float(
            r.get("Median 12 months") or r.get("Typical value")
        ),
    }
