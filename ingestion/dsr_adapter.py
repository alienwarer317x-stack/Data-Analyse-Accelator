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
