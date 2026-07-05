"""将程序化世界导出为 GeoJSON。"""

from __future__ import annotations

import math
from typing import Any

from uav_virtual_validation.world.geo import GeoOrigin, meters_to_latlon, rotate_along_route
from uav_virtual_validation.world.models import Building, GeneratedWorld, NoFlyZone, WeatherSample


def _box_polygon(world: GeneratedWorld, building: Building) -> list[list[float]]:
    origin = GeoOrigin(world.origin_lat, world.origin_lon)
    corners = [
        (-building.width_m / 2.0, -building.depth_m / 2.0),
        (building.width_m / 2.0, -building.depth_m / 2.0),
        (building.width_m / 2.0, building.depth_m / 2.0),
        (-building.width_m / 2.0, building.depth_m / 2.0),
        (-building.width_m / 2.0, -building.depth_m / 2.0),
    ]
    coords = []
    for dx, dy in corners:
        east, north = rotate_along_route(
            building.center_x_m + dx,
            building.center_y_m + dy,
            world.route_heading_deg,
        )
        lat, lon = meters_to_latlon(origin, east, north)
        coords.append([lon, lat])
    return coords


def _circle_polygon(world: GeneratedWorld, zone: NoFlyZone, segments: int = 48) -> list[list[float]]:
    origin = GeoOrigin(world.origin_lat, world.origin_lon)
    coords = []
    for idx in range(segments + 1):
        angle = 2.0 * math.pi * idx / segments
        lateral_x = zone.center_x_m + math.cos(angle) * zone.radius_m
        lateral_y = zone.center_y_m + math.sin(angle) * zone.radius_m
        east, north = rotate_along_route(lateral_x, lateral_y, world.route_heading_deg)
        lat, lon = meters_to_latlon(origin, east, north)
        coords.append([lon, lat])
    return coords


def _weather_point(world: GeneratedWorld, sample: WeatherSample) -> list[float]:
    origin = GeoOrigin(world.origin_lat, world.origin_lon)
    east, north = rotate_along_route(sample.x_m, sample.y_m, world.route_heading_deg)
    lat, lon = meters_to_latlon(origin, east, north)
    return [lon, lat, sample.altitude_m]


def world_to_geojson(world: GeneratedWorld) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for building in world.buildings:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": building.id,
                    "layer": "building",
                    "height_m": round(building.height_m, 2),
                    "risk_score_add": round(building.risk_score_add, 2),
                    "kind": building.kind,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [_box_polygon(world, building)],
                },
            }
        )
    for zone in world.no_fly_zones:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": zone.name,
                    "layer": "no_fly_zone",
                    "radius_m": zone.radius_m,
                    "min_altitude_m": zone.min_altitude_m,
                    "max_altitude_m": zone.max_altitude_m,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [_circle_polygon(world, zone)],
                },
            }
        )
    features.append(
        {
            "type": "Feature",
            "properties": {"layer": "route", "route_length_m": round(world.route_length_m, 2)},
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for lat, lon in world.route_points],
            },
        }
    )
    for sample in world.weather_samples:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "layer": "weather_sample",
                    "wind_speed_mps": round(sample.wind_speed_mps, 2),
                    "wind_dir_deg": round(sample.wind_dir_deg, 1),
                    "temperature_c": round(sample.temperature_c, 2),
                    "pressure_hpa": round(sample.pressure_hpa, 2),
                    "turbulence_index": round(sample.turbulence_index, 3),
                    "altitude_m": sample.altitude_m,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": _weather_point(world, sample),
                },
            }
        )
    return {"type": "FeatureCollection", "name": world.name, "features": features}
