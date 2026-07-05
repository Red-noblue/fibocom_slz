"""基础地理与几何工具：提供经纬度换算、距离估计与二维碰撞判断。"""

from __future__ import annotations

import math
from dataclasses import dataclass


EARTH_RADIUS_M = 6371000.0


@dataclass(frozen=True)
class GeoOrigin:
    lat: float
    lon: float


def latlon_to_meters(origin: GeoOrigin, lat: float, lon: float) -> tuple[float, float]:
    y_m = math.radians(lat - origin.lat) * EARTH_RADIUS_M
    x_m = math.radians(lon - origin.lon) * EARTH_RADIUS_M * math.cos(math.radians(origin.lat))
    return x_m, y_m


def meters_to_latlon(origin: GeoOrigin, x_m: float, y_m: float) -> tuple[float, float]:
    lat = origin.lat + math.degrees(y_m / EARTH_RADIUS_M)
    lon = origin.lon + math.degrees(x_m / (EARTH_RADIUS_M * math.cos(math.radians(origin.lat))))
    return lat, lon


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    d_lat = lat2_rad - lat1_rad
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2.0) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    y = math.sin(delta_lon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def bbox_intersects(
    left_a: float,
    bottom_a: float,
    right_a: float,
    top_a: float,
    left_b: float,
    bottom_b: float,
    right_b: float,
    top_b: float,
) -> bool:
    return not (right_a < left_b or right_b < left_a or top_a < bottom_b or top_b < bottom_a)


def point_in_poly(point: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for idx in range(len(poly) - 1):
        x1, y1 = poly[idx]
        x2, y2 = poly[idx + 1]
        if (y1 > y) != (y2 > y):
            cross_x = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-30) + x1
            if x < cross_x:
                inside = not inside
    return inside


def orient(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return (
        min(a[0], b[0]) <= c[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
        and abs(orient(a, b, c)) < 1e-9
    )


def segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return on_segment(a, b, c) or on_segment(a, b, d) or on_segment(c, d, a) or on_segment(c, d, b)


def segment_hits_poly(a: tuple[float, float], b: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    if point_in_poly(a, poly) or point_in_poly(b, poly):
        return True
    for idx in range(len(poly) - 1):
        if segments_intersect(a, b, poly[idx], poly[idx + 1]):
            return True
    return False
