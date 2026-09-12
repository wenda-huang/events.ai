from math import atan2, cos, radians, sin, sqrt

EARTH_MI = 3958.8
DEFAULT_LAT = 40.4406
DEFAULT_LNG = -79.9959
PITTSBURGH_LAT = DEFAULT_LAT
PITTSBURGH_LNG = DEFAULT_LNG


def haversine_mi(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return EARTH_MI * 2 * atan2(sqrt(a), sqrt(1 - a))


def within_radius(
    origin_lat: float,
    origin_lng: float,
    lat: float,
    lng: float,
    radius_mi: float,
) -> bool:
    return haversine_mi(origin_lat, origin_lng, lat, lng) <= radius_mi
