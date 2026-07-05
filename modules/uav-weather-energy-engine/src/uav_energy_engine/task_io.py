# 负责把任务 JSON 配置解析为统一的任务/载具/电池输入对象。
"""任务输入解析工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple, Union

from .config import load_config
from .predict import load_defaults_from_features, parse_departure
from .schema import BatterySpec, GeoPoint, MissionSpec, RouteSegmentSpec, VehicleSpec


def _resolve_path(value: Union[str, Path], root: Union[str, Path, None] = None) -> Path:
    """解析绝对或相对路径。"""

    path = Path(value)
    if path.is_absolute() or root is None:
        return path
    return Path(root) / path


def _read_payload(path: Union[str, Path]) -> Any:
    """按后缀读取 JSON/YAML 任务配置。"""

    config_path = Path(path)
    if config_path.suffix.lower() == ".json":
        return json.loads(config_path.read_text(encoding="utf-8"))
    return load_config(config_path)


def _point_from_dict(payload: dict) -> GeoPoint:
    """把字典解析为地理点。"""

    return GeoPoint(
        lat=float(payload["lat"]),
        lon=float(payload["lon"]),
        alt_m=float(payload.get("alt_m", 0.0)),
    )


def _segment_from_dict(payload: dict) -> RouteSegmentSpec:
    """把字典解析为单段路线。"""

    return RouteSegmentSpec(
        start=_point_from_dict(payload["start"]),
        end=_point_from_dict(payload["end"]),
        duration_s=float(payload["duration_s"]),
        distance_m=float(payload["distance_m"]) if payload.get("distance_m") is not None else None,
        segment_id=int(payload["segment_id"]) if payload.get("segment_id") is not None else None,
    )


def _payload_g(task_cfg: dict, defaults: dict) -> float:
    """读取载荷重量，优先任务配置，其次训练默认值。"""

    if "vehicle" in task_cfg and "payload_g" in task_cfg["vehicle"]:
        return float(task_cfg["vehicle"]["payload_g"])
    if "payload_g" in defaults:
        return float(defaults["payload_g"])
    if "payload_kg" in defaults:
        return float(defaults["payload_kg"]) * 1000.0
    return 0.0


def load_task_bundle(
    task_config: Union[str, Path],
    features_path: Union[str, Path],
) -> Tuple[MissionSpec, VehicleSpec, BatterySpec, dict]:
    """从任务配置和训练样本默认值构建统一输入对象。"""

    task_path = Path(task_config)
    task_cfg = _read_payload(task_path)
    defaults = load_defaults_from_features(features_path)

    route_points = [_point_from_dict(row) for row in task_cfg.get("route_points", [])]
    route_segments = [_segment_from_dict(row) for row in task_cfg.get("route_segments", [])]
    start_payload = task_cfg.get("start") or (task_cfg["route_points"][0] if route_points else None)
    end_payload = task_cfg.get("end") or (task_cfg["route_points"][-1] if route_points else None)
    if start_payload is None and route_segments:
        start_payload = {
            "lat": route_segments[0].start.lat,
            "lon": route_segments[0].start.lon,
            "alt_m": route_segments[0].start.alt_m,
        }
    if end_payload is None and route_segments:
        end_payload = {
            "lat": route_segments[-1].end.lat,
            "lon": route_segments[-1].end.lon,
            "alt_m": route_segments[-1].end.alt_m,
        }
    if start_payload is None or end_payload is None:
        raise ValueError("任务配置至少需要 start/end，或提供 route_points/route_segments。")

    mission = MissionSpec(
        route_name=str(task_cfg.get("route_name", "task_route")),
        start=_point_from_dict(start_payload),
        end=_point_from_dict(end_payload),
        departure_time=parse_departure(str(task_cfg["departure_time"])),
        step_minutes=int(task_cfg.get("mission", {}).get("step_minutes", defaults.get("step_minutes", 1))),
        route_points=route_points,
        route_segments=route_segments,
    )
    vehicle_cfg = task_cfg.get("vehicle", {})
    battery_cfg = task_cfg.get("battery", {})
    vehicle = VehicleSpec(
        name=str(vehicle_cfg.get("name", "deployment_vehicle")),
        payload_g=_payload_g(task_cfg, defaults),
        cruise_speed_mps=float(vehicle_cfg.get("cruise_speed_mps", defaults["speed_mps"])),
        altitude_m=float(vehicle_cfg.get("altitude_m", defaults["altitude_m"])),
        max_speed_mps=float(vehicle_cfg["max_speed_mps"]) if "max_speed_mps" in vehicle_cfg else None,
        hover_power_w=float(vehicle_cfg["hover_power_w"]) if "hover_power_w" in vehicle_cfg else None,
    )
    battery = BatterySpec(
        capacity_wh=float(battery_cfg.get("capacity_wh", 130.0)),
        nominal_voltage_v=float(battery_cfg.get("nominal_voltage_v", 15.2)),
    )
    return mission, vehicle, battery, task_cfg
