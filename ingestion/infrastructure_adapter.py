import pandas as pd
import os
import math


def haversine(lat1, lon1, lat2, lon2):
    """Distance between two lat/lon points in km."""
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_csv(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            return None
    return None


_SCHOOLS = load_csv(os.path.join("data", "schools.csv"))
_HOSPITALS = load_csv(os.path.join("data", "hospitals.csv"))


def get_infrastructure_profile(lat, lon, radius_km=10):
    profile = {
        "schools": [],
        "hospitals": []
    }

    if lat is None or lon is None:
        return profile

    if _SCHOOLS is not None:
        for _, r in _SCHOOLS.iterrows():
            d = haversine(lat, lon, r["Latitude"], r["Longitude"])
            if d <= radius_km:
                profile["schools"].append({
                    "name": r["SchoolName"],
                    "type": r["Type"],
                    "distance_km": round(d, 1)
                })

    if _HOSPITALS is not None:
        for _, r in _HOSPITALS.iterrows():
            d = haversine(lat, lon, r["Latitude"], r["Longitude"])
            if d <= radius_km:
                profile["hospitals"].append({
                    "name": r["HospitalName"],
                    "type": r["Type"],
                    "distance_km": round(d, 1)
                })

    return profile
