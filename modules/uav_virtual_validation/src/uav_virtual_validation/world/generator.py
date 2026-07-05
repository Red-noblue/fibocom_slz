"""生成城市高楼、禁飞区和三维天气场的程序化世界。"""

from __future__ import annotations

import math
import random
from typing import Any

from uav_virtual_validation.simulators.simple import bearing_deg, haversine_m
from uav_virtual_validation.world.geo import GeoOrigin, meters_to_latlon, rotate_along_route
from uav_virtual_validation.world.models import Building, GeneratedWorld, NoFlyZone, WeatherSample


def _route_point(origin: GeoOrigin, along_m: float, lateral_m: float, heading_deg: float) -> tuple[float, float]:
    east, north = rotate_along_route(along_m, lateral_m, heading_deg)
    return meters_to_latlon(origin, east, north)


def _inside_highrise_zone(world_cfg: dict[str, Any], fraction: float) -> bool:
    zone = world_cfg.get("highrise_zone", {})
    return float(zone.get("start_fraction", 1.0)) <= fraction <= float(zone.get("end_fraction", 0.0))


def generate_world(scenario: dict[str, Any], world_cfg: dict[str, Any]) -> GeneratedWorld:
    start = scenario["start"]
    end = scenario["end"]
    origin = GeoOrigin(float(start["lat"]), float(start["lon"]))
    route_length_m = haversine_m(start["lat"], start["lon"], end["lat"], end["lon"])
    heading = bearing_deg(start["lat"], start["lon"], end["lat"], end["lon"])
    rng = random.Random(int(world_cfg.get("seed", 0)))

    city_length = route_length_m + 2.0 * float(world_cfg["city_length_margin_m"])
    city_width = float(world_cfg["city_width_m"])
    block = float(world_cfg["block_size_m"])
    street = float(world_cfg["street_width_m"])
    min_h = float(world_cfg["building_min_height_m"])
    max_h = float(world_cfg["building_max_height_m"])
    margin = float(world_cfg["city_length_margin_m"])

    buildings: list[Building] = []
    along = -margin
    building_idx = 0
    while along <= city_length - margin:
        lateral = -city_width / 2.0
        while lateral <= city_width / 2.0:
            fraction = max(0.0, min(1.0, along / max(route_length_m, 1.0)))
            highrise = _inside_highrise_zone(world_cfg, fraction)
            density = float(world_cfg.get("highrise_zone", {}).get("density_multiplier", 1.0)) if highrise else 1.0
            if rng.random() < min(0.88, 0.58 * density):
                usable = max(20.0, block - street)
                width = rng.uniform(usable * 0.42, usable * 0.92)
                depth = rng.uniform(usable * 0.42, usable * 0.92)
                height = rng.uniform(min_h, max_h)
                kind = "midrise"
                if highrise:
                    height += rng.uniform(0.25, 1.0) * float(world_cfg.get("highrise_zone", {}).get("extra_height_m", 0.0))
                    kind = "highrise" if height >= 110.0 else "dense_midrise"
                distance_to_route = abs(lateral)
                risk = max(0.0, (height - 60.0) * 0.08) + max(0.0, 260.0 - distance_to_route) * 0.025
                buildings.append(
                    Building(
                        id=f"bldg_{building_idx:05d}",
                        center_x_m=along + rng.uniform(-street * 0.45, street * 0.45),
                        center_y_m=lateral + rng.uniform(-street * 0.45, street * 0.45),
                        width_m=width,
                        depth_m=depth,
                        height_m=height,
                        risk_score_add=risk,
                        kind=kind,
                    )
                )
                building_idx += 1
            lateral += block
        along += block

    no_fly_zones = [
        NoFlyZone(
            name=str(zone["name"]),
            center_x_m=float(zone["center_fraction"]) * route_length_m,
            center_y_m=float(zone["lateral_offset_m"]),
            radius_m=float(zone["radius_m"]),
            min_altitude_m=float(zone.get("min_altitude_m", 0.0)),
            max_altitude_m=float(zone.get("max_altitude_m", 120.0)),
        )
        for zone in world_cfg.get("no_fly_zones", [])
    ]

    weather = scenario["weather"]
    field = world_cfg.get("weather_field", {})
    spacing = float(field.get("sample_spacing_m", 600.0))
    altitudes = [float(v) for v in field.get("altitude_layers_m", [100.0])]
    weather_samples: list[WeatherSample] = []
    x = 0.0
    while x <= route_length_m:
        y = -city_width / 2.0
        while y <= city_width / 2.0:
            fraction = x / max(route_length_m, 1.0)
            highrise = _inside_highrise_zone(world_cfg, fraction)
            canyon = 1.0 if abs(y) < float(world_cfg.get("route_corridor_width_m", 500.0)) / 2.0 else 0.0
            for altitude in altitudes:
                shear = math.log(max(altitude, 11.0) / 10.0) / math.log(100.0 / 10.0)
                wind = float(weather["wind_speed_mps"]) * (0.72 + 0.28 * shear)
                wind += math.sin(fraction * math.pi * 4.0 + y / 500.0) * 0.55
                turbulence = 0.12 + canyon * float(field.get("urban_canyon_turbulence_bonus", 0.0))
                if highrise:
                    wind += float(field.get("highrise_wind_shear_bonus", 0.0)) * wind
                    turbulence += 0.28
                temp = float(weather["temperature_c"]) - altitude * 0.0065 + (0.35 if canyon else 0.0)
                pressure = float(weather["pressure_hpa"]) * math.exp(-altitude / 8434.5)
                weather_samples.append(
                    WeatherSample(
                        x_m=x,
                        y_m=y,
                        altitude_m=altitude,
                        wind_speed_mps=max(0.0, wind),
                        wind_dir_deg=float(weather["wind_dir_deg"]),
                        temperature_c=temp,
                        pressure_hpa=pressure,
                        turbulence_index=min(1.0, turbulence),
                    )
                )
            y += spacing
        x += spacing

    route_points = [
        _route_point(origin, route_length_m * i / 64.0, 0.0, heading)
        for i in range(65)
    ]
    return GeneratedWorld(
        name=str(world_cfg["name"]),
        origin_lat=origin.lat,
        origin_lon=origin.lon,
        route_heading_deg=heading,
        route_length_m=route_length_m,
        route_points=route_points,
        buildings=buildings,
        no_fly_zones=no_fly_zones,
        weather_samples=weather_samples,
    )
