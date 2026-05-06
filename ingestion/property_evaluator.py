def score_property_asset(attributes: dict) -> dict:
    """
    Evaluates an individual property based on specific physical traits.
    Attributes: land_size, frontage, orientation, street_type, condition.
    """
    score = 70  # Baseline for a 'standard' house
    deductions = []
    boosters = []

    # --- THE HARD GATES (Deductions) ---
    if attributes.get("on_main_road"):
        score -= 25
        deductions.append("Main Road Interface (High Resale Risk)")
        
    if attributes.get("under_power_lines"):
        score -= 15
        deductions.append("Proximity to High Voltage Lines")

    # --- THE PREMIUM BOOSTERS (Additions) ---
    if attributes.get("land_size", 0) > 600:
        score += 10
        boosters.append("Substantial Land Component (>600sqm)")

    if attributes.get("north_facing_rear"):
        score += 8
        boosters.append("Optimal North-Facing Rear (Natural Light)")

    if attributes.get("frontage_metres", 0) >= 15:
        score += 7
        boosters.append("Wide Frontage (>15m) - Future Development Potential")

    # --- FINAL GRADING ---
    if score >= 80:
        grade = "A-Grade Asset"
    elif score >= 65:
        grade = "B-Grade Asset"
    else:
        grade = "C-Grade (High Risk / Low Growth)"

    return {
        "asset_score": score,
        "grade": grade,
        "positives": boosters,
        "negatives": deductions
    }
