"""仿真世界数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Building:
    id: str
    center_x_m: float
    center_y_m: float
    width_m: float
    depth_m: float
    height_m: float
    risk_score_add: float
    kind: str


@dataclass(frozen=True)
class NoFlyZone:
    name: str
    center_x_m: float
    center_y_m: float
    radius_m: float
    min_altitude_m: float
    max_altitude_m: float


@dataclass(frozen=True)
class WeatherSample:
    x_m: float
    y_m: float
    altitude_m: float
    wind_speed_mps: float
    wind_dir_deg: float
    temperature_c: float
    pressure_hpa: float
    turbulence_index: float


@dataclass(frozen=True)
class GeneratedWorld:
    name: str
    origin_lat: float
    origin_lon: float
    route_heading_deg: float
    route_length_m: float
    route_points: list[tuple[float, float]]
    buildings: list[Building]
    no_fly_zones: list[NoFlyZone]
    weather_samples: list[WeatherSample]
