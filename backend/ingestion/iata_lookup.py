"""
IATA airport coordinates for great-circle distance calculation.

This is a curated subset of major airports. In production you'd load
this from a full dataset or an external API.
"""

# {IATA_CODE: (latitude, longitude)}
IATA_COORDINATES: dict[str, tuple[float, float]] = {
    # North America
    "ATL": (33.6407, -84.4277),
    "ORD": (41.9742, -87.9073),
    "DFW": (32.8998, -97.0403),
    "DEN": (39.8561, -104.6737),
    "JFK": (40.6413, -73.7781),
    "LAX": (33.9425, -118.4081),
    "SFO": (37.6213, -122.3790),
    "SEA": (47.4502, -122.3088),
    "MIA": (25.7959, -80.2870),
    "BOS": (42.3656, -71.0096),
    "EWR": (40.6895, -74.1745),
    "IAH": (29.9902, -95.3368),
    "MSP": (44.8848, -93.2223),
    "DTW": (42.2124, -83.3534),
    "PHL": (39.8729, -75.2437),
    "LGA": (40.7769, -73.8740),
    "YYZ": (43.6777, -79.6248),
    "YVR": (49.1967, -123.1815),
    "MEX": (19.4363, -99.0721),
    # Europe
    "LHR": (51.4700, -0.4543),
    "CDG": (49.0097, 2.5479),
    "FRA": (50.0379, 8.5622),
    "AMS": (52.3105, 4.7683),
    "MAD": (40.4983, -3.5676),
    "BCN": (41.2974, 2.0833),
    "FCO": (41.8003, 12.2389),
    "MUC": (48.3537, 11.7750),
    "ZRH": (47.4647, 8.5492),
    "VIE": (48.1103, 16.5697),
    "CPH": (55.6180, 12.6508),
    "OSL": (60.1976, 11.1004),
    "ARN": (59.6519, 17.9186),
    "HEL": (60.3172, 24.9633),
    "DUB": (53.4264, -6.2499),
    "LIS": (38.7742, -9.1342),
    "IST": (41.2753, 28.7519),
    # Asia
    "HND": (35.5494, 139.7798),
    "NRT": (35.7647, 140.3864),
    "PEK": (40.0799, 116.6031),
    "PVG": (31.1443, 121.8083),
    "HKG": (22.3080, 113.9185),
    "SIN": (1.3644, 103.9915),
    "BKK": (13.6900, 100.7501),
    "ICN": (37.4602, 126.4407),
    "DEL": (28.5562, 77.1000),
    "BOM": (19.0896, 72.8656),
    "BLR": (13.1979, 77.7063),
    "DXB": (25.2532, 55.3657),
    "DOH": (25.2731, 51.6081),
    # Oceania
    "SYD": (-33.9461, 151.1772),
    "MEL": (-37.6690, 144.8410),
    "AKL": (-37.0082, 174.7850),
    # Africa
    "JNB": (-26.1392, 28.2460),
    "CPT": (-33.9649, 18.6017),
    "CAI": (30.1219, 31.4056),
    "NBO": (-1.3192, 36.9278),
    "LOS": (6.5774, 3.3212),
    # South America
    "GRU": (-23.4356, -46.4731),
    "EZE": (-34.8222, -58.5358),
    "BOG": (4.7016, -74.1469),
    "SCL": (-33.3930, -70.7858),
    "LIM": (-12.0219, -77.1143),
}


def get_great_circle_distance_km(origin: str, destination: str) -> float | None:
    """
    Compute great-circle distance in km between two IATA airport codes.

    Uses the geopy library's geodesic distance calculator.
    Returns None if either code is unknown.
    """
    origin = origin.upper().strip()
    destination = destination.upper().strip()

    coord_a = IATA_COORDINATES.get(origin)
    coord_b = IATA_COORDINATES.get(destination)

    if not coord_a or not coord_b:
        return None

    try:
        from geopy.distance import geodesic
        return round(geodesic(coord_a, coord_b).km, 2)
    except Exception:
        # Fallback: Haversine formula
        import math
        lat1, lon1 = math.radians(coord_a[0]), math.radians(coord_a[1])
        lat2, lon2 = math.radians(coord_b[0]), math.radians(coord_b[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth radius in km
        return round(r * c, 2)
