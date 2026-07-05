# 提供固定路线固定航速条件下的能耗预测逻辑，并兼容分段级能耗模型。
"""提供固定路线固定航速条件下的能耗预测逻辑。"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
import pandas as pd

from .features import (
    DIRECT_WEATHER_MODEL_COLUMNS,
    build_model_feature_row,
    compute_air_density,
    compute_weather_factor,
    compute_wind_components,
    ensure_planned_ground_speed,
    to_frame,
)
from .model import WeatherEnergyModel
from .reachability import apply_conservative_reachability, load_reachability_safety_profile
from .schema import BatterySpec, GeoPoint, MissionSpec, PredictionBundle, RouteSegmentSpec, SegmentPrediction, VehicleSpec
from .target_modes import infer_target_mode, segment_energy_from_single_prediction
from .utils import bearing_deg, ensure_dir, haversine_m
from .weather import (
    GenericWeatherClient,
    build_route_points,
    build_weather_request_window,
    circular_interp_deg,
    estimate_aqi,
    estimate_visibility_km,
    fetch_open_meteo_aqi,
    height_aware_wind,
    interp_optional,
    interpolate_weather,
    row_value,
)


def parse_departure(value: str) -> datetime:
    """解析起飞时间。"""

    if value.lower() == "now":
        return datetime.now()
    return pd.to_datetime(value).to_pydatetime()


def load_defaults_from_features(features_path: Union[str, Path]) -> dict:
    """从训练样本中加载默认飞行参数。"""

    df = ensure_planned_ground_speed(pd.read_csv(features_path))
    payload_g = None
    if "payload_g" in df.columns:
        payload_g = float(pd.to_numeric(df["payload_g"], errors="coerce").median())
    elif "payload_kg" in df.columns:
        payload_g = float(pd.to_numeric(df["payload_kg"], errors="coerce").median()) * 1000.0
    else:
        payload_g = 0.0
    defaults = {
        "speed_mps": float(df["planned_ground_speed_mps"].median()),
        "payload_g": payload_g,
        "payload_kg": payload_g / 1000.0,
        "altitude_m": float(df["altitude_m"].median()),
    }
    if "duration_s" in df.columns:
        duration_s = pd.to_numeric(df["duration_s"], errors="coerce").median()
        if np.isfinite(duration_s) and duration_s > 0:
            defaults["segment_duration_s"] = float(duration_s)
            defaults["step_minutes"] = max(1, int(round(float(duration_s) / 60.0)))
    return defaults


def detect_weather_source(config_path: Union[str, Path]) -> str:
    """根据天气配置识别天气数据源名称。"""

    cfg = json.loads(Path(config_path).read_text(encoding="utf-8")) if str(config_path).endswith(".json") else None
    if cfg is None:
        from .config import load_config

        cfg = load_config(config_path)
    base_url = str(cfg.get("base_url", "")).lower()
    if "open-meteo.com" in base_url:
        return "Open-Meteo"
    if "cma" in base_url:
        return "CMA"
    return "Config-driven weather source"


def model_predicts_segment_energy(model: WeatherEnergyModel) -> bool:
    """判断模型输出是否为分段总耗电。"""

    return infer_target_mode(getattr(model, "target", "")) == "segment_energy_wh"


def build_risk_alerts(summary: dict) -> List[str]:
    """根据预测结果生成风险提示。"""

    alerts = []
    total_energy = float(summary["predicted_total_energy_wh"])
    battery_wh = float(summary["battery_wh"])
    route_length_km = float(summary["route_length_km"])
    predicted_range_km = float(summary["predicted_range_km"])

    if total_energy > battery_wh:
        alerts.append("预测总能耗高于电池容量，任务存在中途电量耗尽风险。")
    if predicted_range_km < route_length_km:
        alerts.append("按当前效率预测的续航里程不足以覆盖全程航线。")

    conservative = summary.get("conservative_reachability")
    if conservative:
        quantiles = conservative.get("quantiles", {})
        p95 = quantiles.get("p95")
        p90 = quantiles.get("p90")
        if p95 and not p95.get("route_feasible", True):
            alerts.append(
                "按 P95 保守估计，任务可能无法安全覆盖全程；建议降低任务距离、增加电池余量或重新规划航线。"
            )
        elif p90 and not p90.get("route_feasible", True):
            alerts.append("按 P90 保守估计，任务存在明显电量余量不足风险。")

    if not alerts:
        alerts.append("当前预测未触发硬性风险，但仍建议结合实时风场复核。")
    return alerts


def add_planned_phase_defaults(feature_row: dict, segment_distance_km: float, segment_duration_s: float) -> dict:
    """为飞行前规划路线补充分段阶段特征，并尽量从路线几何推断阶段。"""

    horizontal_speed = float(segment_distance_km * 1000.0 / segment_duration_s) if segment_duration_s > 1e-9 else 0.0
    is_slow = horizontal_speed < 0.7
    altitude_delta_m = float(feature_row.get("altitude_delta_m", 0.0) or 0.0)
    vertical_speed = altitude_delta_m / segment_duration_s if segment_duration_s > 1e-9 else 0.0
    heading_change_deg = float(feature_row.get("segment_heading_change_deg", 0.0) or 0.0)
    turn_rate_deg_s = abs(heading_change_deg) / segment_duration_s if segment_duration_s > 1e-9 else 0.0
    is_climb = vertical_speed > 0.3
    is_descent = vertical_speed < -0.3
    is_turn = abs(heading_change_deg) >= 20.0 or turn_rate_deg_s >= 3.0
    is_level = not (is_climb or is_descent)
    is_hover = is_slow and abs(vertical_speed) < 0.3
    is_cruise = (not is_hover) and is_level
    defaults = {
        "climb_ratio": 1.0 if is_climb else 0.0,
        "descent_ratio": 1.0 if is_descent else 0.0,
        "level_ratio": 1.0 if is_level else 0.0,
        "turn_ratio": 1.0 if is_turn else 0.0,
        "hover_or_slow_ratio": 1.0 if is_hover else 0.0,
        "cruise_ratio": 1.0 if is_cruise else 0.0,
        "vertical_speed_mean_mps": vertical_speed,
        "vertical_speed_abs_mean_mps": abs(vertical_speed),
        "vertical_speed_abs_p95_mps": abs(vertical_speed),
        "horizontal_speed_mean_mps": horizontal_speed,
        "horizontal_speed_std_mps": 0.0,
        "horizontal_speed_p95_mps": horizontal_speed,
        "acceleration_abs_mean_mps2": 0.0,
        "acceleration_abs_p95_mps2": 0.0,
        "turn_rate_mean_deg_s": turn_rate_deg_s,
        "turn_rate_p95_deg_s": turn_rate_deg_s,
        "phase_is_climb": 1.0 if is_climb else 0.0,
        "phase_is_descent": 1.0 if is_descent else 0.0,
        "phase_is_level": 1.0 if is_level else 0.0,
        "phase_is_turn": 1.0 if is_turn else 0.0,
        "phase_is_hover_or_slow": 1.0 if is_hover else 0.0,
        "phase_is_cruise": 1.0 if is_cruise else 0.0,
    }
    for key, value in defaults.items():
        feature_row[key] = value
    return feature_row


def apply_hover_power_prior(
    vehicle: VehicleSpec,
    feature_row: dict,
    segment_duration_s: float,
    segment_ground_speed_mps: float,
    segment_energy_wh: float,
) -> float:
    """当任务显式提供悬停功率校准时，为悬停/极低速段提供能耗下限。"""

    hover_power_w = getattr(vehicle, "hover_power_w", None)
    if hover_power_w is None or not np.isfinite(float(hover_power_w)) or float(hover_power_w) <= 0.0:
        return float(segment_energy_wh)
    if float(segment_duration_s) <= 1e-9:
        return float(segment_energy_wh)
    is_hover_phase = float(feature_row.get("phase_is_hover_or_slow", 0.0) or 0.0) >= 0.5
    if not is_hover_phase:
        return float(segment_energy_wh)
    if float(segment_ground_speed_mps) > 0.3:
        return float(segment_energy_wh)
    hover_energy_wh = float(hover_power_w) * float(segment_duration_s) / 3600.0
    return float(max(segment_energy_wh, hover_energy_wh))


def add_planned_route_geometry_defaults(
    feature_row: dict,
    route_distance_m: float,
    segment_distance_m: float,
    segment_start_distance_m: float,
    route_heading_deg: float,
    route_segment_count: int,
) -> dict:
    """为固定路线推理补充与训练一致的路线几何特征。"""

    route_distance = max(float(route_distance_m), 0.0)
    segment_distance = max(float(segment_distance_m), 0.0)
    segment_mid_distance = max(float(segment_start_distance_m), 0.0) + segment_distance / 2.0
    route_distance_km = route_distance / 1000.0
    heading_rad = np.deg2rad(float(route_heading_deg))
    route_progress_ratio = segment_mid_distance / route_distance if route_distance > 1e-9 else 0.0
    route_remaining_distance_m = max(0.0, route_distance - segment_mid_distance)

    defaults = {
        "heading_sin": float(np.sin(heading_rad)),
        "heading_cos": float(np.cos(heading_rad)),
        "route_direct_distance_m": route_distance,
        "route_total_distance_m": route_distance,
        "route_tortuosity": 1.0,
        "route_segment_count": int(route_segment_count),
        "route_progress_ratio": float(route_progress_ratio),
        "route_remaining_distance_m": float(route_remaining_distance_m),
        "route_distance_share": float(segment_distance / route_distance) if route_distance > 1e-9 else 0.0,
        "route_total_heading_change_deg": 0.0,
        "route_turn_density_deg_per_km": 0.0,
        "segment_heading_change_deg": 0.0,
        "segment_turn_density_deg_per_km": 0.0,
        "route_bearing_deg": float(route_heading_deg),
        "route_bearing_sin": float(np.sin(heading_rad)),
        "route_bearing_cos": float(np.cos(heading_rad)),
        "segment_route_alignment": 1.0,
        "segment_route_cross_alignment": 0.0,
        "route_total_altitude_gain_m": 0.0,
        "route_total_altitude_loss_m": 0.0,
        "route_altitude_range_m": 0.0,
        "route_climb_density_m_per_km": 0.0 if route_distance_km > 1e-9 else 0.0,
        "route_descent_density_m_per_km": 0.0 if route_distance_km > 1e-9 else 0.0,
    }
    for key, value in defaults.items():
        feature_row.setdefault(key, value)
    return feature_row


def add_segment_altitude_defaults(
    feature_row: dict,
    start_point: GeoPoint,
    end_point: GeoPoint,
    segment_duration_s: float,
) -> dict:
    """根据分段起终点高度补充垂直动态特征。"""

    route_altitude_default = float(feature_row.get("altitude_m", 0.0) or 0.0)
    start_alt = float(start_point.alt_m)
    end_alt = float(end_point.alt_m)
    if not np.isfinite(start_alt):
        start_alt = route_altitude_default
    if not np.isfinite(end_alt):
        end_alt = route_altitude_default
    altitude_delta_m = end_alt - start_alt
    feature_row["altitude_start_m"] = start_alt
    feature_row["altitude_end_m"] = end_alt
    feature_row["altitude_delta_m"] = altitude_delta_m
    feature_row["altitude_range_m"] = abs(altitude_delta_m)
    feature_row["altitude_gain_m"] = max(altitude_delta_m, 0.0)
    feature_row["altitude_loss_m"] = max(-altitude_delta_m, 0.0)
    if segment_duration_s > 1e-9:
        vertical_speed = altitude_delta_m / segment_duration_s
        feature_row["vertical_speed_mean_mps"] = vertical_speed
        feature_row["vertical_speed_abs_mean_mps"] = abs(vertical_speed)
        feature_row["vertical_speed_abs_p95_mps"] = abs(vertical_speed)
    return feature_row


def write_prediction_outputs(
    bundle: PredictionBundle,
    output_dir: Union[str, Path],
) -> Tuple[Path, Path]:
    """将预测结果写入目录。"""

    output_path = Path(output_dir)
    ensure_dir(output_path)
    summary_path = output_path / "summary.json"
    timeseries_path = output_path / "timeseries.csv"

    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(bundle.summary, fh, indent=2, ensure_ascii=False)

    frame = pd.DataFrame([segment.__dict__ for segment in bundle.segments])
    frame.to_csv(timeseries_path, index=False)
    return summary_path, timeseries_path


def load_weather_frame(weather_input: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
    """加载本地天气时序表，供离线回放评估复用。"""

    if isinstance(weather_input, pd.DataFrame):
        frame = weather_input.copy()
    else:
        path = Path(weather_input)
        frame = pd.read_csv(path)
    time_col = None
    for candidate in ["time", "mid_time", "start_time", "datetime"]:
        if candidate in frame.columns:
            time_col = candidate
            break
    if time_col is None:
        raise ValueError("本地天气表缺少时间列，至少需要 time/mid_time/start_time/datetime 之一。")
    frame[time_col] = pd.to_datetime(frame[time_col], errors="coerce")
    frame = frame.dropna(subset=[time_col]).copy()
    frame = frame.set_index(pd.DatetimeIndex(frame[time_col])).drop(columns=[time_col])
    frame.index.name = "time"
    return frame.sort_index()


def mission_route_points(mission: MissionSpec, steps: int) -> List[GeoPoint]:
    """读取任务航线点；缺省时回退到起终点直线插值。"""

    if len(mission.route_points) >= 2:
        return list(mission.route_points)
    return build_route_points(mission.start, mission.end, steps)


def route_total_distance_m(route_points: List[GeoPoint]) -> float:
    """计算航线总长度。"""

    if len(route_points) < 2:
        return 0.0
    total = 0.0
    for start, end in zip(route_points[:-1], route_points[1:]):
        total += float(haversine_m(start.lat, start.lon, end.lat, end.lon))
    return total


def resample_route_points(route_points: List[GeoPoint], target_steps: int) -> List[GeoPoint]:
    """按累计里程重采样航线点，保证预测步数与路线点数一致。"""

    if target_steps <= 1:
        return [route_points[0], route_points[-1]] if len(route_points) >= 2 else list(route_points)
    if len(route_points) < 2:
        return list(route_points)
    if len(route_points) == target_steps:
        return list(route_points)

    cumulative = [0.0]
    for start, end in zip(route_points[:-1], route_points[1:]):
        cumulative.append(cumulative[-1] + float(haversine_m(start.lat, start.lon, end.lat, end.lon)))
    total_distance = cumulative[-1]
    if total_distance <= 1e-9:
        return [route_points[0]] * target_steps

    targets = np.linspace(0.0, total_distance, target_steps)
    sampled: List[GeoPoint] = []
    segment_idx = 0
    for target_distance in targets:
        while segment_idx < len(cumulative) - 2 and cumulative[segment_idx + 1] < target_distance:
            segment_idx += 1
        start = route_points[segment_idx]
        end = route_points[segment_idx + 1]
        start_distance = cumulative[segment_idx]
        end_distance = cumulative[segment_idx + 1]
        if end_distance - start_distance <= 1e-9:
            frac = 0.0
        else:
            frac = (target_distance - start_distance) / (end_distance - start_distance)
        sampled.append(
            GeoPoint(
                lat=float(start.lat + (end.lat - start.lat) * frac),
                lon=float(start.lon + (end.lon - start.lon) * frac),
                alt_m=float(start.alt_m + (end.alt_m - start.alt_m) * frac),
            )
        )
    return sampled


def mission_segment_specs(mission: MissionSpec, vehicle: VehicleSpec) -> list[dict]:
    """优先读取任务显式提供的路线分段；缺失时从 route_points 构造。"""

    if mission.route_segments:
        specs = []
        elapsed_start_s = 0.0
        for index, segment in enumerate(mission.route_segments):
            distance_m = (
                float(segment.distance_m)
                if segment.distance_m is not None
                else float(haversine_m(segment.start.lat, segment.start.lon, segment.end.lat, segment.end.lon))
            )
            duration_s = float(segment.duration_s)
            elapsed_end_s = elapsed_start_s + duration_s
            midpoint_s = elapsed_start_s + duration_s / 2.0
            specs.append(
                {
                    "segment_id": int(segment.segment_id if segment.segment_id is not None else index),
                    "start": segment.start,
                    "end": segment.end,
                    "distance_m": distance_m,
                    "duration_s": duration_s,
                    "elapsed_start_s": elapsed_start_s,
                    "elapsed_end_s": elapsed_end_s,
                    "midpoint_s": midpoint_s,
                }
            )
            elapsed_start_s = elapsed_end_s
        return specs

    points = _legacy_route_points_for_mission(mission, vehicle)
    segment_specs = []
    elapsed_start_s = 0.0
    for segment_id, (start, end) in enumerate(zip(points[:-1], points[1:])):
        distance_m = float(haversine_m(start.lat, start.lon, end.lat, end.lon))
        if distance_m <= 0.0:
            continue
        duration_s = distance_m / float(vehicle.cruise_speed_mps)
        elapsed_end_s = elapsed_start_s + duration_s
        midpoint_s = elapsed_start_s + duration_s / 2.0
        segment_specs.append(
            {
                "segment_id": segment_id,
                "start": start,
                "end": end,
                "distance_m": distance_m,
                "duration_s": duration_s,
                "elapsed_start_s": elapsed_start_s,
                "elapsed_end_s": elapsed_end_s,
                "midpoint_s": midpoint_s,
            }
        )
        elapsed_start_s = elapsed_end_s
    return segment_specs


def segment_boundary_time_index(mission: MissionSpec, segment_specs: list[dict]) -> pd.DatetimeIndex:
    """按真实分段累计时长构造边界时间轴，避免变时长分段被均匀步长抹平。"""

    offsets_s = [0.0]
    elapsed_s = 0.0
    for spec in segment_specs:
        elapsed_s += float(spec["duration_s"])
        offsets_s.append(elapsed_s)
    return pd.DatetimeIndex(
        [mission.departure_time + timedelta(seconds=float(offset_s)) for offset_s in offsets_s]
    )


def _legacy_route_points_for_mission(mission: MissionSpec, vehicle: VehicleSpec) -> List[GeoPoint]:
    """兼容旧逻辑：没有显式分段时，根据 route_points 或直线插值构造航点。"""

    if len(mission.route_points) >= 2:
        return list(mission.route_points)
    total_distance_m = float(haversine_m(mission.start.lat, mission.start.lon, mission.end.lat, mission.end.lon))
    total_time_s = total_distance_m / float(vehicle.cruise_speed_mps)
    step_seconds = max(1, int(mission.step_minutes) * 60)
    point_count = max(2, int(np.ceil(total_time_s / step_seconds)) + 1)
    return build_route_points(mission.start, mission.end, point_count)


def predict_fixed_route_energy(
    model_path: Union[str, Path],
    weather_config: Union[str, Path],
    mission: MissionSpec,
    vehicle: VehicleSpec,
    battery: BatterySpec,
    safety_profile: Union[str, Path, dict, None] = None,
) -> PredictionBundle:
    """执行固定路线固定航速条件下的能耗预测。"""

    model = WeatherEnergyModel.load(model_path)
    model_uses_direct_weather = any(column in model.feature_cols for column in DIRECT_WEATHER_MODEL_COLUMNS)
    model_target_mode = infer_target_mode(getattr(model, "target", ""))
    segment_specs = mission_segment_specs(mission, vehicle)
    if not segment_specs:
        raise ValueError("任务没有可用路线分段。")
    total_distance_m = float(sum(float(spec["distance_m"]) for spec in segment_specs))
    total_distance_km = total_distance_m / 1000.0
    heading_deg = float(bearing_deg(mission.start.lat, mission.start.lon, mission.end.lat, mission.end.lon))
    total_time_s = float(sum(float(spec["duration_s"]) for spec in segment_specs))
    step_seconds = max(1, int(round(float(pd.Series([spec["duration_s"] for spec in segment_specs]).median()))))
    steps = len(segment_specs) + 1
    time_index = segment_boundary_time_index(mission, segment_specs)
    route_points = [segment_specs[0]["start"]] + [spec["end"] for spec in segment_specs]
    mission_end = mission.departure_time + timedelta(seconds=total_time_s)

    weather_client = GenericWeatherClient(weather_config)
    weather_window_params = build_weather_request_window(weather_config, mission.departure_time, mission_end)
    start_weather = weather_client.fetch_hourly(mission.start, extra_params=weather_window_params)
    end_weather = weather_client.fetch_hourly(mission.end, extra_params=weather_window_params)
    start_interp = interpolate_weather(start_weather, time_index)
    end_interp = interpolate_weather(end_weather, time_index)

    try:
        from .config import load_config

        cfg = load_config(weather_config)
        base_url = str(cfg.get("base_url", "")).lower()
        timezone = str(cfg.get("timezone") or cfg.get("params", {}).get("timezone") or "Asia/Shanghai")
    except Exception:
        base_url = ""
        timezone = "Asia/Shanghai"

    if "open-meteo.com" in base_url:
        try:
            forecast_hours = pd.to_numeric(
                pd.Series([weather_window_params.get("forecast_hours")]),
                errors="coerce",
            ).iloc[0]
            forecast_hours = int(forecast_hours) if np.isfinite(forecast_hours) else None
            aqi_start = fetch_open_meteo_aqi(mission.start, timezone, forecast_hours=forecast_hours)
            aqi_end = fetch_open_meteo_aqi(mission.end, timezone, forecast_hours=forecast_hours)
            if not aqi_start.empty:
                start_interp["air_quality_index"] = interpolate_weather(aqi_start, time_index)["air_quality_index"].to_numpy()
            if not aqi_end.empty:
                end_interp["air_quality_index"] = interpolate_weather(aqi_end, time_index)["air_quality_index"].to_numpy()
        except Exception:
            pass

    cumulative = [0.0]
    for spec in segment_specs:
        cumulative.append(cumulative[-1] + float(spec["distance_m"]))
    distances = np.asarray(cumulative, dtype=float)
    cumulative_energy = 0.0
    reachable_distance_m = total_distance_m
    reachable_time_s = total_time_s
    depleted = False
    segments: List[SegmentPrediction] = []

    for idx in range(steps):
        frac = distances[idx] / total_distance_m if total_distance_m > 0 else 0.0
        weather_start = start_interp.iloc[idx]
        weather_end = end_interp.iloc[idx]

        segment_heading_deg = heading_deg
        if idx < len(segment_specs):
            segment_heading_deg = float(
                bearing_deg(
                    segment_specs[idx]["start"].lat,
                    segment_specs[idx]["start"].lon,
                    segment_specs[idx]["end"].lat,
                    segment_specs[idx]["end"].lon,
                )
            )
        start_wind_speed, start_wind_dir = height_aware_wind(weather_start, vehicle.altitude_m)
        end_wind_speed, end_wind_dir = height_aware_wind(weather_end, vehicle.altitude_m)
        wind_speed = float(start_wind_speed * (1.0 - frac) + end_wind_speed * frac)
        wind_dir = circular_interp_deg(start_wind_dir, end_wind_dir, frac)
        headwind, crosswind = compute_wind_components(wind_speed, wind_dir, segment_heading_deg)
        temperature_c = float(weather_start["temperature_c"] * (1.0 - frac) + weather_end["temperature_c"] * frac)
        relative_humidity_pct = float(
            weather_start["relative_humidity_pct"] * (1.0 - frac)
            + weather_end["relative_humidity_pct"] * frac
        )
        pressure_hpa = float(weather_start["pressure_hpa"] * (1.0 - frac) + weather_end["pressure_hpa"] * frac)
        precipitation_mm = float(
            weather_start["precipitation_mm"] * (1.0 - frac)
            + weather_end["precipitation_mm"] * frac
        )

        visibility_km = interp_optional(weather_start, weather_end, frac, ["visibility_km"], default=np.nan)
        if not np.isfinite(visibility_km):
            visibility_m = interp_optional(
                weather_start,
                weather_end,
                frac,
                ["visibility_m", "visibility"],
                default=np.nan,
            )
            if np.isfinite(visibility_m):
                visibility_km = visibility_m / 1000.0
        if not np.isfinite(visibility_km):
            visibility_km = estimate_visibility_km(relative_humidity_pct, precipitation_mm, wind_speed)
        visibility_km = float(np.clip(visibility_km, 0.2, 30.0))

        uv_index = interp_optional(
            weather_start,
            weather_end,
            frac,
            ["uv_index", "uv", "ultraviolet_index"],
            default=np.nan,
        )
        if not np.isfinite(uv_index):
            uv_index = 2.0 if 9 <= time_index[idx].hour <= 16 else 0.0
        uv_index = float(np.clip(uv_index, 0.0, 16.0))

        air_quality_index = interp_optional(
            weather_start,
            weather_end,
            frac,
            ["air_quality_index", "us_aqi", "european_aqi", "aqi"],
            default=np.nan,
        )
        if not np.isfinite(air_quality_index):
            air_quality_index = estimate_aqi(
                visibility_km,
                relative_humidity_pct,
                wind_speed,
                precipitation_mm,
                pressure_hpa,
            )
        air_quality_index = float(np.clip(air_quality_index, 0.0, 500.0))

        if idx == 0:
            segment_distance_km = 0.0
            energy_wh_per_km = 0.0
            segment_energy_wh = 0.0
            weather_factor = 1.0
        else:
            seg_dist_m = float(segment_specs[idx - 1]["distance_m"])
            segment_distance_km = seg_dist_m / 1000.0
            segment_duration_s = float(segment_specs[idx - 1]["duration_s"])
            segment_ground_speed_mps = seg_dist_m / segment_duration_s if segment_duration_s > 1e-9 else float(vehicle.cruise_speed_mps)
            wind_gust_mps = interp_optional(
                weather_start,
                weather_end,
                frac,
                ["wind_gust_mps", "wind_gusts_10m", "gust", "fg10"],
                default=np.nan,
            )
            air_density_kgm3 = (
                compute_air_density(temperature_c=temperature_c, pressure_hpa=pressure_hpa)
                if np.isfinite(temperature_c) and np.isfinite(pressure_hpa)
                else np.nan
            )
            feature_row = build_model_feature_row(
                speed_mps=segment_ground_speed_mps,
                payload_g=vehicle.payload_g,
                altitude_m=vehicle.altitude_m,
                wind_speed_mps=wind_speed,
                wind_dir_deg=wind_dir,
                heading_deg=segment_heading_deg,
                wind_gust_mps=wind_gust_mps,
                temperature_c=temperature_c,
                relative_humidity_pct=relative_humidity_pct,
                pressure_hpa=pressure_hpa,
                precipitation_mm=precipitation_mm,
                air_density_kgm3=air_density_kgm3,
            )
            feature_row["heading_deg"] = segment_heading_deg
            feature_row["distance_m"] = seg_dist_m
            feature_row["duration_s"] = segment_duration_s
            feature_row = add_segment_altitude_defaults(
                feature_row=feature_row,
                start_point=segment_specs[idx - 1]["start"],
                end_point=segment_specs[idx - 1]["end"],
                segment_duration_s=segment_duration_s,
            )
            feature_row = add_planned_route_geometry_defaults(
                feature_row=feature_row,
                route_distance_m=total_distance_m,
                segment_distance_m=seg_dist_m,
                segment_start_distance_m=float(distances[idx - 1]),
                route_heading_deg=segment_heading_deg,
                route_segment_count=max(1, len(segment_specs)),
            )
            feature_row["segment_heading_change_deg"] = float(
                abs(
                    (
                        segment_heading_deg
                        - float(
                            bearing_deg(
                                segment_specs[idx - 2]["start"].lat,
                                segment_specs[idx - 2]["start"].lon,
                                segment_specs[idx - 2]["end"].lat,
                                segment_specs[idx - 2]["end"].lon,
                            )
                        )
                        + 180.0
                    )
                    % 360.0
                    - 180.0
                )
            ) if idx >= 2 else 0.0
            feature_row = add_planned_phase_defaults(feature_row, segment_distance_km, segment_duration_s)
            feature_row["hist_wind_speed_mps"] = feature_row["wind_speed_mps"]
            feature_row["hist_wind_dir_deg"] = feature_row.get("wind_dir_deg", wind_dir)
            feature_row["hist_headwind_mps"] = feature_row["headwind_mps"]
            feature_row["hist_crosswind_mps"] = feature_row["crosswind_mps"]
            feature_row["hist_wind_gust_mps"] = feature_row.get("wind_gust_mps", np.nan)
            feature_row["hist_relative_humidity_pct"] = feature_row.get("relative_humidity_pct", np.nan)
            feature_row["hist_temperature_c"] = feature_row.get("temperature_c", np.nan)
            feature_row["hist_pressure_hpa"] = feature_row.get("pressure_hpa", np.nan)
            feature_row["hist_precipitation_mm"] = feature_row.get("precipitation_mm", np.nan)
            feature_row["hist_air_density_kgm3"] = feature_row.get("air_density_kgm3", np.nan)
            feature_row["wind_speed_max"] = wind_speed
            feature_row["wind_speed_std"] = 0.0
            feature_row["wind_speed_p95"] = wind_speed
            feature_row["hist_wind_speed_mps_max"] = wind_speed
            feature_row["hist_wind_speed_mps_std"] = 0.0
            feature_row["hist_wind_gust_mps_max"] = feature_row.get("wind_gust_mps", np.nan)
            feature_row["hist_temperature_c_std"] = 0.0
            feature_row["hist_pressure_hpa_std"] = 0.0
            model_output = float(model.predict(to_frame(feature_row))[0])
            if model_uses_direct_weather:
                weather_factor = 1.0
            else:
                weather_factor = compute_weather_factor(
                    temperature_c=temperature_c,
                    relative_humidity_pct=relative_humidity_pct,
                    pressure_hpa=pressure_hpa,
                    precipitation_mm=precipitation_mm,
                    visibility_km=visibility_km,
                    uv_index=uv_index,
                    air_quality_index=air_quality_index,
                )
            segment_energy_wh = segment_energy_from_single_prediction(
                model_output=model_output,
                target=getattr(model, "target", ""),
                segment_distance_km=segment_distance_km,
                segment_duration_s=segment_duration_s,
                multiplier=weather_factor,
            )
            segment_energy_wh = apply_hover_power_prior(
                vehicle=vehicle,
                feature_row=feature_row,
                segment_duration_s=segment_duration_s,
                segment_ground_speed_mps=segment_ground_speed_mps,
                segment_energy_wh=segment_energy_wh,
            )
            energy_wh_per_km = segment_energy_wh / segment_distance_km if segment_distance_km > 1e-9 else 0.0
            cumulative_energy += segment_energy_wh

            if (not depleted) and cumulative_energy >= battery.capacity_wh:
                depleted = True
                excess = cumulative_energy - battery.capacity_wh
                frac_seg = max(0.0, 1.0 - excess / segment_energy_wh) if segment_energy_wh > 0 else 0.0
                reachable_distance_m = float(distances[idx - 1] + seg_dist_m * frac_seg)
                reachable_time_s = float(segment_specs[idx - 1]["elapsed_start_s"] + segment_duration_s * frac_seg)

        segments.append(
            SegmentPrediction(
                time=time_index[idx].isoformat(),
                lat=route_points[idx].lat,
                lon=route_points[idx].lon,
                distance_from_start_km=float(distances[idx] / 1000.0),
                segment_distance_km=float(segment_distance_km),
                wind_speed_mps=float(wind_speed),
                wind_dir_deg=float(wind_dir),
                headwind_mps=float(headwind),
                crosswind_mps=float(crosswind),
                temperature_c=float(temperature_c),
                relative_humidity_pct=float(relative_humidity_pct),
                pressure_hpa=float(pressure_hpa),
                precipitation_mm=float(precipitation_mm),
                visibility_km=float(visibility_km),
                uv_index=float(uv_index),
                air_quality_index=float(air_quality_index),
                weather_factor=float(weather_factor),
                energy_wh_per_km=float(energy_wh_per_km),
                segment_energy_wh=float(segment_energy_wh),
                cumulative_energy_wh=float(cumulative_energy),
                remaining_battery_wh=max(0.0, float(battery.capacity_wh - cumulative_energy)),
            )
        )

    summary = {
        "route_name": mission.route_name,
        "route_start": {"lat": mission.start.lat, "lon": mission.start.lon},
        "route_end": {"lat": mission.end.lat, "lon": mission.end.lon},
        "route_heading_deg": heading_deg,
        "route_length_km": total_distance_km,
        "route_point_count": int(len(route_points)),
        "cruise_speed_mps": vehicle.cruise_speed_mps,
        "cruise_altitude_m": vehicle.altitude_m,
        "payload_g": vehicle.payload_g,
        "battery_wh": battery.capacity_wh,
        "departure_time": mission.departure_time.isoformat(),
        "prediction_step_minutes": int(mission.step_minutes),
        "prediction_step_seconds": int(step_seconds),
        "planned_flight_time_s": total_time_s,
        "predicted_total_energy_wh": float(sum(segment.segment_energy_wh for segment in segments)),
        "predicted_range_km": reachable_distance_m / 1000.0,
        "predicted_flight_time_s": reachable_time_s,
        "weather_source": detect_weather_source(weather_config),
        "model_target": getattr(model, "target", ""),
        "model_target_mode": model_target_mode,
    }
    if safety_profile is not None:
        profile = load_reachability_safety_profile(safety_profile)
        summary["conservative_reachability"] = apply_conservative_reachability(summary, profile)
    summary["risk_alerts"] = build_risk_alerts(summary)
    return PredictionBundle(summary=summary, segments=segments)


def predict_fixed_route_energy_with_weather_frame(
    model_path: Union[str, Path],
    weather_frame: Union[str, Path, pd.DataFrame],
    mission: MissionSpec,
    vehicle: VehicleSpec,
    battery: BatterySpec,
    weather_source: str = "offline_weather_frame",
    safety_profile: Union[str, Path, dict, None] = None,
) -> PredictionBundle:
    """使用本地天气时序表执行固定路线预测，服务历史任务回放评估。"""

    model = WeatherEnergyModel.load(model_path)
    model_uses_direct_weather = any(column in model.feature_cols for column in DIRECT_WEATHER_MODEL_COLUMNS)
    model_target_mode = infer_target_mode(getattr(model, "target", ""))
    segment_specs = mission_segment_specs(mission, vehicle)
    if not segment_specs:
        raise ValueError("任务没有可用路线分段。")
    total_distance_m = float(sum(float(spec["distance_m"]) for spec in segment_specs))
    total_distance_km = total_distance_m / 1000.0
    heading_deg = float(bearing_deg(mission.start.lat, mission.start.lon, mission.end.lat, mission.end.lon))
    total_time_s = float(sum(float(spec["duration_s"]) for spec in segment_specs))
    step_seconds = max(1, int(round(float(pd.Series([spec["duration_s"] for spec in segment_specs]).median()))))
    steps = len(segment_specs) + 1
    time_index = segment_boundary_time_index(mission, segment_specs)
    route_points = [segment_specs[0]["start"]] + [spec["end"] for spec in segment_specs]
    weather_frame_loaded = load_weather_frame(weather_frame)
    aligned_weather = interpolate_weather(weather_frame_loaded, time_index)

    cumulative = [0.0]
    for spec in segment_specs:
        cumulative.append(cumulative[-1] + float(spec["distance_m"]))
    distances = np.asarray(cumulative, dtype=float)

    cumulative_energy = 0.0
    reachable_distance_m = total_distance_m
    reachable_time_s = total_time_s
    depleted = False
    segments: List[SegmentPrediction] = []

    for idx in range(steps):
        frac = distances[idx] / total_distance_m if total_distance_m > 0 else 0.0
        weather_row = aligned_weather.iloc[idx]
        segment_heading_deg = heading_deg
        if idx < len(segment_specs):
            segment_heading_deg = float(
                bearing_deg(
                    segment_specs[idx]["start"].lat,
                    segment_specs[idx]["start"].lon,
                    segment_specs[idx]["end"].lat,
                    segment_specs[idx]["end"].lon,
                )
            )
        wind_speed, wind_dir = height_aware_wind(weather_row, vehicle.altitude_m)
        headwind, crosswind = compute_wind_components(wind_speed, wind_dir, segment_heading_deg)
        temperature_c = row_value(weather_row, ["temperature_c", "temp_c"], np.nan)
        relative_humidity_pct = row_value(weather_row, ["relative_humidity_pct", "humidity_pct"], np.nan)
        pressure_hpa = row_value(weather_row, ["pressure_hpa", "pressure_msl_hpa"], np.nan)
        precipitation_mm = row_value(weather_row, ["precipitation_mm", "precipitation"], np.nan)
        visibility_km = row_value(weather_row, ["visibility_km"], np.nan)
        if not np.isfinite(visibility_km):
            visibility_m = row_value(weather_row, ["visibility_m", "visibility"], np.nan)
            if np.isfinite(visibility_m):
                visibility_km = visibility_m / 1000.0
        if not np.isfinite(visibility_km):
            visibility_km = estimate_visibility_km(relative_humidity_pct, precipitation_mm, wind_speed)
        uv_index = row_value(weather_row, ["uv_index", "uv"], 0.0)
        air_quality_index = row_value(weather_row, ["air_quality_index", "us_aqi", "aqi"], np.nan)
        if not np.isfinite(air_quality_index):
            air_quality_index = estimate_aqi(
                visibility_km,
                relative_humidity_pct,
                wind_speed,
                precipitation_mm,
                pressure_hpa,
            )
        if idx == 0:
            segment_distance_km = 0.0
            segment_energy_wh = 0.0
            energy_wh_per_km = 0.0
            weather_factor = 1.0
        else:
            seg_dist_m = float(segment_specs[idx - 1]["distance_m"])
            segment_distance_km = seg_dist_m / 1000.0
            segment_duration_s = float(segment_specs[idx - 1]["duration_s"])
            segment_ground_speed_mps = seg_dist_m / segment_duration_s if segment_duration_s > 1e-9 else float(vehicle.cruise_speed_mps)
            wind_gust_mps = row_value(weather_row, ["wind_gust_mps", "wind_gusts_10m"], np.nan)
            air_density_kgm3 = (
                compute_air_density(temperature_c=temperature_c, pressure_hpa=pressure_hpa)
                if np.isfinite(temperature_c) and np.isfinite(pressure_hpa)
                else np.nan
            )
            feature_row = build_model_feature_row(
                speed_mps=segment_ground_speed_mps,
                payload_g=vehicle.payload_g,
                altitude_m=vehicle.altitude_m,
                wind_speed_mps=wind_speed,
                wind_dir_deg=wind_dir,
                heading_deg=segment_heading_deg,
                wind_gust_mps=wind_gust_mps,
                temperature_c=temperature_c,
                relative_humidity_pct=relative_humidity_pct,
                pressure_hpa=pressure_hpa,
                precipitation_mm=precipitation_mm,
                air_density_kgm3=air_density_kgm3,
            )
            feature_row["heading_deg"] = segment_heading_deg
            feature_row["distance_m"] = seg_dist_m
            feature_row["duration_s"] = segment_duration_s
            feature_row = add_segment_altitude_defaults(
                feature_row=feature_row,
                start_point=segment_specs[idx - 1]["start"],
                end_point=segment_specs[idx - 1]["end"],
                segment_duration_s=segment_duration_s,
            )
            feature_row = add_planned_route_geometry_defaults(
                feature_row=feature_row,
                route_distance_m=total_distance_m,
                segment_distance_m=seg_dist_m,
                segment_start_distance_m=float(distances[idx - 1]),
                route_heading_deg=segment_heading_deg,
                route_segment_count=max(1, len(segment_specs)),
            )
            feature_row["segment_heading_change_deg"] = float(
                abs(
                    (
                        segment_heading_deg
                        - float(
                            bearing_deg(
                                segment_specs[idx - 2]["start"].lat,
                                segment_specs[idx - 2]["start"].lon,
                                segment_specs[idx - 2]["end"].lat,
                                segment_specs[idx - 2]["end"].lon,
                            )
                        )
                        + 180.0
                    )
                    % 360.0
                    - 180.0
                )
            ) if idx >= 2 else 0.0
            feature_row = add_planned_phase_defaults(feature_row, segment_distance_km, segment_duration_s)
            model_output = float(model.predict(to_frame(feature_row))[0])
            weather_factor = 1.0 if model_uses_direct_weather else compute_weather_factor(
                temperature_c=temperature_c,
                relative_humidity_pct=relative_humidity_pct,
                pressure_hpa=pressure_hpa,
                precipitation_mm=precipitation_mm,
                visibility_km=visibility_km,
                uv_index=uv_index,
                air_quality_index=air_quality_index,
            )
            segment_energy_wh = segment_energy_from_single_prediction(
                model_output=model_output,
                target=getattr(model, "target", ""),
                segment_distance_km=segment_distance_km,
                segment_duration_s=segment_duration_s,
                multiplier=weather_factor,
            )
            segment_energy_wh = apply_hover_power_prior(
                vehicle=vehicle,
                feature_row=feature_row,
                segment_duration_s=segment_duration_s,
                segment_ground_speed_mps=segment_ground_speed_mps,
                segment_energy_wh=segment_energy_wh,
            )
            energy_wh_per_km = segment_energy_wh / segment_distance_km if segment_distance_km > 1e-9 else 0.0
            cumulative_energy += segment_energy_wh
            if (not depleted) and cumulative_energy >= battery.capacity_wh:
                depleted = True
                excess = cumulative_energy - battery.capacity_wh
                frac_seg = max(0.0, 1.0 - excess / segment_energy_wh) if segment_energy_wh > 0 else 0.0
                reachable_distance_m = float(distances[idx - 1] + seg_dist_m * frac_seg)
                reachable_time_s = float(segment_specs[idx - 1]["elapsed_start_s"] + segment_duration_s * frac_seg)
        segments.append(
            SegmentPrediction(
                time=time_index[idx].isoformat(),
                lat=route_points[idx].lat,
                lon=route_points[idx].lon,
                distance_from_start_km=float(distances[idx] / 1000.0),
                segment_distance_km=float(segment_distance_km),
                wind_speed_mps=float(wind_speed),
                wind_dir_deg=float(wind_dir),
                headwind_mps=float(headwind),
                crosswind_mps=float(crosswind),
                temperature_c=float(temperature_c),
                relative_humidity_pct=float(relative_humidity_pct),
                pressure_hpa=float(pressure_hpa),
                precipitation_mm=float(precipitation_mm),
                visibility_km=float(visibility_km),
                uv_index=float(uv_index),
                air_quality_index=float(air_quality_index),
                weather_factor=float(weather_factor),
                energy_wh_per_km=float(energy_wh_per_km),
                segment_energy_wh=float(segment_energy_wh),
                cumulative_energy_wh=float(cumulative_energy),
                remaining_battery_wh=max(0.0, float(battery.capacity_wh - cumulative_energy)),
            )
        )

    summary = {
        "route_name": mission.route_name,
        "route_start": {"lat": mission.start.lat, "lon": mission.start.lon},
        "route_end": {"lat": mission.end.lat, "lon": mission.end.lon},
        "route_heading_deg": heading_deg,
        "route_length_km": total_distance_km,
        "route_point_count": int(len(route_points)),
        "cruise_speed_mps": vehicle.cruise_speed_mps,
        "cruise_altitude_m": vehicle.altitude_m,
        "payload_g": vehicle.payload_g,
        "battery_wh": battery.capacity_wh,
        "departure_time": mission.departure_time.isoformat(),
        "prediction_step_minutes": int(mission.step_minutes),
        "prediction_step_seconds": int(step_seconds),
        "planned_flight_time_s": total_time_s,
        "predicted_total_energy_wh": float(sum(segment.segment_energy_wh for segment in segments)),
        "predicted_range_km": reachable_distance_m / 1000.0,
        "predicted_flight_time_s": reachable_time_s,
        "weather_source": weather_source,
        "model_target": getattr(model, "target", ""),
        "model_target_mode": model_target_mode,
    }
    if safety_profile is not None:
        profile = load_reachability_safety_profile(safety_profile)
        summary["conservative_reachability"] = apply_conservative_reachability(summary, profile)
    summary["risk_alerts"] = build_risk_alerts(summary)
    return PredictionBundle(summary=summary, segments=segments)
