"""把城市级天气扩展为真实城市任务验证用的三维天气采样场。"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from uav_virtual_validation.simulators.simple import bearing_deg, haversine_m
from uav_virtual_validation.world.geo import GeoOrigin, meters_to_latlon, rotate_along_route


def _first_hour(payload: dict[str, Any], key: str, default: float) -> float:
    values = payload.get("hourly", {}).get(key, [])
    if not values:
        return default
    value = values[0]
    return float(value) if value is not None else default


def _route_length_and_heading(route: list[dict[str, Any]]) -> tuple[float, float]:
    total = 0.0
    for idx in range(1, len(route)):
        prev = route[idx - 1]
        cur = route[idx]
        total += haversine_m(prev["lat"], prev["lon"], cur["lat"], cur["lon"])
    heading = bearing_deg(route[0]["lat"], route[0]["lon"], route[-1]["lat"], route[-1]["lon"])
    return total, heading


def build_real_weather_field_geojson(
    city: dict[str, Any],
    weather_payload: dict[str, Any],
    along_samples: int = 10,
    lateral_offsets_m: list[float] | None = None,
    altitude_layers_m: list[float] | None = None,
) -> dict[str, Any]:
    route = city["default_route"]
    lateral_offsets_m = lateral_offsets_m or [-450.0, -270.0, -90.0, 90.0, 270.0, 450.0]
    altitude_layers_m = altitude_layers_m or [30.0, 60.0, 100.0, 150.0, 220.0]
    origin = GeoOrigin(float(route[0]["lat"]), float(route[0]["lon"]))
    route_length_m, heading = _route_length_and_heading(route)

    base_temp = _first_hour(weather_payload, "temperature_2m", 18.0)
    base_pressure = _first_hour(weather_payload, "pressure_msl", 1013.0)
    base_rh = _first_hour(weather_payload, "relative_humidity_2m", 65.0)
    base_wind = _first_hour(weather_payload, "wind_speed_10m", 3.0)
    base_dir = _first_hour(weather_payload, "wind_direction_10m", heading)
    base_gust = _first_hour(weather_payload, "wind_gusts_10m", base_wind)
    precip = _first_hour(weather_payload, "precipitation", 0.0)
    cloud = _first_hour(weather_payload, "cloud_cover", 40.0)

    features: list[dict[str, Any]] = []
    bbox = city.get("bbox")
    if bbox:
        rows = len(lateral_offsets_m)
        for i in range(along_samples):
            frac_x = i / max(along_samples - 1, 1)
            lon = float(bbox["west"]) + (float(bbox["east"]) - float(bbox["west"])) * frac_x
            for j in range(rows):
                frac_y = j / max(rows - 1, 1)
                lat = float(bbox["south"]) + (float(bbox["north"]) - float(bbox["south"])) * frac_y
                urban_canyon = 1.0 - abs(frac_y - 0.5) * 2.0
                for altitude in altitude_layers_m:
                    shear = math.log(max(altitude, 11.0) / 10.0) / math.log(100.0 / 10.0)
                    wind = base_wind * (0.72 + 0.28 * shear)
                    wind += math.sin(frac_x * math.pi * 3.0 + frac_y * math.pi * 2.0) * 0.45
                    gust_factor = max(0.0, base_gust - base_wind) * 0.18
                    turbulence = min(1.0, 0.12 + urban_canyon * 0.32 + gust_factor * 0.08)
                    temp = base_temp - altitude * 0.0065 + urban_canyon * 0.25
                    pressure = base_pressure * math.exp(-altitude / 8434.5)
                    features.append(
                        {
                            "type": "Feature",
                            "properties": {
                                "layer": "weather_sample",
                                "source": "open_meteo_bbox_field",
                                "altitude_m": altitude,
                                "wind_speed_mps": round(max(0.0, wind), 2),
                                "wind_dir_deg": round(base_dir, 1),
                                "temperature_c": round(temp, 2),
                                "pressure_hpa": round(pressure, 2),
                                "relative_humidity_pct": round(base_rh, 1),
                                "precipitation_mm": round(precip, 3),
                                "cloud_cover_pct": round(cloud, 1),
                                "turbulence_index": round(turbulence, 3),
                                "grid_x": i,
                                "grid_y": j,
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": [lon, lat, altitude],
                            },
                        }
                    )
        return {
            "type": "FeatureCollection",
            "name": f"{city['name']}_real_weather_field",
            "features": features,
        }

    for i in range(along_samples):
        frac = i / max(along_samples - 1, 1)
        along = route_length_m * frac
        for lateral in lateral_offsets_m:
            urban_canyon = max(0.0, 1.0 - abs(lateral) / max(abs(max(lateral_offsets_m)), 1.0))
            for altitude in altitude_layers_m:
                shear = math.log(max(altitude, 11.0) / 10.0) / math.log(100.0 / 10.0)
                wind = base_wind * (0.72 + 0.28 * shear)
                wind += math.sin(frac * math.pi * 3.0 + lateral / 260.0) * 0.45
                gust_factor = max(0.0, base_gust - base_wind) * 0.18
                turbulence = min(1.0, 0.12 + urban_canyon * 0.32 + gust_factor * 0.08)
                temp = base_temp - altitude * 0.0065 + urban_canyon * 0.25
                pressure = base_pressure * math.exp(-altitude / 8434.5)
                east, north = rotate_along_route(along, lateral, heading)
                lat, lon = meters_to_latlon(origin, east, north)
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "layer": "weather_sample",
                            "source": "open_meteo_derived_field",
                            "altitude_m": altitude,
                            "wind_speed_mps": round(max(0.0, wind), 2),
                            "wind_dir_deg": round(base_dir, 1),
                            "temperature_c": round(temp, 2),
                            "pressure_hpa": round(pressure, 2),
                            "relative_humidity_pct": round(base_rh, 1),
                            "precipitation_mm": round(precip, 3),
                            "cloud_cover_pct": round(cloud, 1),
                            "turbulence_index": round(turbulence, 3),
                            "route_fraction": round(frac, 3),
                            "lateral_offset_m": lateral,
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat, altitude],
                        },
                    }
                )
    return {
        "type": "FeatureCollection",
        "name": f"{city['name']}_real_weather_field",
        "features": features,
    }


def build_weather_field_from_files(city_path: str | Path, weather_path: str | Path) -> dict[str, Any]:
    with Path(city_path).open("r", encoding="utf-8") as fh:
        city = json.load(fh)
    with Path(weather_path).open("r", encoding="utf-8") as fh:
        weather = json.load(fh)
    return build_real_weather_field_geojson(city, weather)
