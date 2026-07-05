from __future__ import annotations

import math
from pathlib import Path

import numpy as np


def ensure_dir(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def haversine_m(lat1, lon1, lat2, lon2):
    radius_m = 6371000.0
    lat1 = np.deg2rad(lat1)
    lon1 = np.deg2rad(lon1)
    lat2 = np.deg2rad(lat2)
    lon2 = np.deg2rad(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arcsin(np.sqrt(a))
    return radius_m * c


def bearing_deg(lat1, lon1, lat2, lon2):
    lat1 = np.deg2rad(lat1)
    lon1 = np.deg2rad(lon1)
    lat2 = np.deg2rad(lat2)
    lon2 = np.deg2rad(lon2)
    dlon = lon2 - lon1
    y = np.sin(dlon) * np.cos(lat2)
    x = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
    bearing = np.rad2deg(np.arctan2(y, x))
    return (bearing + 360.0) % 360.0


def circular_mean_deg(angles_deg, weights=None):
    angles = np.asarray(angles_deg, dtype=float)
    if angles.size == 0 or np.all(np.isnan(angles)):
        return float("nan")

    angles = np.deg2rad(angles)
    if weights is None:
        weights = np.ones_like(angles)
    weights = np.asarray(weights, dtype=float)

    sin_sum = np.nansum(np.sin(angles) * weights)
    cos_sum = np.nansum(np.cos(angles) * weights)
    if math.isclose(sin_sum, 0.0) and math.isclose(cos_sum, 0.0):
        return float("nan")

    mean = np.rad2deg(np.arctan2(sin_sum, cos_sum))
    return (mean + 360.0) % 360.0
