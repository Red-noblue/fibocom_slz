"""局部平面坐标与经纬度之间的轻量转换。"""

from __future__ import annotations

import math
from dataclasses import dataclass


EARTH_RADIUS_M = 6371000.0


@dataclass(frozen=True)
class GeoOrigin:
    lat: float
    lon: float


def meters_to_latlon(origin: GeoOrigin, x_m: float, y_m: float) -> tuple[float, float]:
    lat = origin.lat + math.degrees(y_m / EARTH_RADIUS_M)
    lon = origin.lon + math.degrees(x_m / (EARTH_RADIUS_M * math.cos(math.radians(origin.lat))))
    return lat, lon


def latlon_to_meters(origin: GeoOrigin, lat: float, lon: float) -> tuple[float, float]:
    y_m = math.radians(lat - origin.lat) * EARTH_RADIUS_M
    x_m = math.radians(lon - origin.lon) * EARTH_RADIUS_M * math.cos(math.radians(origin.lat))
    return x_m, y_m


def rotate_along_route(along_m: float, lateral_m: float, heading_deg: float) -> tuple[float, float]:
    heading = math.radians(heading_deg)
    east = along_m * math.sin(heading) + lateral_m * math.sin(heading + math.pi / 2.0)
    north = along_m * math.cos(heading) + lateral_m * math.cos(heading + math.pi / 2.0)
    return east, north
