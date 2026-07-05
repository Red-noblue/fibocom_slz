# 定义天气驱动无人机能耗引擎的核心输入输出对象。
"""定义天气驱动无人机能耗引擎的核心输入输出对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class GeoPoint:
    """定义地理点。"""

    lat: float
    lon: float
    alt_m: float = 0.0


@dataclass
class RouteSegmentSpec:
    """定义任务中的单段路线计划。"""

    start: GeoPoint
    end: GeoPoint
    duration_s: float
    distance_m: Optional[float] = None
    segment_id: Optional[int] = None


@dataclass
class BatterySpec:
    """定义电池参数。"""

    capacity_wh: float
    nominal_voltage_v: float = 15.2


@dataclass
class VehicleSpec:
    """定义无人机动力学相关输入参数。"""

    name: str
    payload_g: float
    cruise_speed_mps: float
    altitude_m: float
    max_speed_mps: Optional[float] = None
    hover_power_w: Optional[float] = None


@dataclass
class MissionSpec:
    """定义任务级输入。"""

    route_name: str
    start: GeoPoint
    end: GeoPoint
    departure_time: datetime
    step_minutes: int = 1
    route_points: list[GeoPoint] = field(default_factory=list)
    route_segments: list[RouteSegmentSpec] = field(default_factory=list)


@dataclass
class SegmentPrediction:
    """定义单段预测结果。"""

    time: str
    lat: float
    lon: float
    distance_from_start_km: float
    segment_distance_km: float
    wind_speed_mps: float
    wind_dir_deg: float
    headwind_mps: float
    crosswind_mps: float
    temperature_c: float
    relative_humidity_pct: float
    pressure_hpa: float
    precipitation_mm: float
    visibility_km: float
    uv_index: float
    air_quality_index: float
    weather_factor: float
    energy_wh_per_km: float
    segment_energy_wh: float
    cumulative_energy_wh: float
    remaining_battery_wh: float


@dataclass
class PredictionBundle:
    """定义单次任务预测输出。"""

    summary: dict[str, Any]
    segments: list[SegmentPrediction]


@dataclass
class EvaluationConfig:
    """定义候选方案评分参数。"""

    infeasible_penalty: float = 10_000.0
    risk_penalty: float = 1_000.0
    speed_change_penalty: float = 0.0
    altitude_change_penalty: float = 0.0


@dataclass
class CandidateScore:
    """定义候选任务方案评分结果。"""

    candidate_id: str
    score: float
    total_energy_wh: float
    route_length_km: float
    predicted_range_km: float
    feasible: bool
    risk_count: int
    summary: dict[str, Any]
