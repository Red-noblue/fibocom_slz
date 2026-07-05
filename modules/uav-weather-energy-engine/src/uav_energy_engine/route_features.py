# 将飞行前天气数据转换为模型统一使用的路线-时间序列特征表。
"""将天气、任务和无人机参数适配为路线-时间序列特征。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import List, Sequence

import numpy as np
import pandas as pd

from .features import compute_air_density, compute_wind_components, ensure_planned_ground_speed
from .planned_equivalent_features import add_planned_equivalent_wind_features
from .schema import GeoPoint, MissionSpec, VehicleSpec
from .utils import bearing_deg, haversine_m
from .weather import build_route_points, height_aware_wind, interpolate_weather, row_value


ROUTE_TIME_ID_COLUMNS = [
    "route_name",
    "segment_id",
    "feature_source",
    "weather_source",
    "start_time",
    "end_time",
    "mid_time",
    "elapsed_start_s",
    "elapsed_end_s",
    "start_lat",
    "start_lon",
    "end_lat",
    "end_lon",
]

ROUTE_TIME_MODEL_FEATURE_COLUMNS = [
    "planned_ground_speed_mps",
    "speed_mps",
    "payload_kg",
    "altitude_m",
    "altitude_start_m",
    "altitude_end_m",
    "altitude_delta_m",
    "altitude_range_m",
    "altitude_gain_m",
    "altitude_loss_m",
    "vertical_speed_mean_mps",
    "vertical_speed_abs_mean_mps",
    "vertical_speed_abs_p95_mps",
    "distance_m",
    "duration_s",
    "heading_deg",
    "wind_speed_mps",
    "wind_dir_deg",
    "headwind_mps",
    "crosswind_mps",
    "equivalent_airspeed_mps",
    "equivalent_along_track_airspeed_mps",
    "equivalent_cross_track_airspeed_mps",
    "equivalent_crosswind_abs_mps",
    "headwind_ratio",
    "crosswind_ratio",
    "tailwind_mps",
    "wind_gust_mps",
    "temperature_c",
    "relative_humidity_pct",
    "pressure_hpa",
    "precipitation_mm",
    "air_density_kgm3",
]

ROUTE_GEOMETRY_FEATURE_COLUMNS = [
    "heading_sin",
    "heading_cos",
    "route_direct_distance_m",
    "route_total_distance_m",
    "route_tortuosity",
    "route_segment_count",
    "route_progress_ratio",
    "route_remaining_distance_m",
    "route_distance_share",
    "route_total_heading_change_deg",
    "route_turn_density_deg_per_km",
    "segment_heading_change_deg",
    "segment_turn_density_deg_per_km",
    "route_bearing_deg",
    "route_bearing_sin",
    "route_bearing_cos",
    "segment_route_alignment",
    "segment_route_cross_alignment",
    "route_total_altitude_gain_m",
    "route_total_altitude_loss_m",
    "route_altitude_range_m",
    "route_climb_density_m_per_km",
    "route_descent_density_m_per_km",
]

ROUTE_TIME_COLUMNS = ROUTE_TIME_ID_COLUMNS + ROUTE_TIME_MODEL_FEATURE_COLUMNS + ROUTE_GEOMETRY_FEATURE_COLUMNS

PREFLIGHT_TRAINING_WEATHER_MAP = {
    "wind_speed_mps": ["hist_height_wind_speed_mps", "hist_wind_speed_mps"],
    "wind_dir_deg": ["hist_height_wind_dir_deg", "hist_wind_dir_deg"],
    "headwind_mps": ["hist_headwind_mps"],
    "crosswind_mps": ["hist_crosswind_mps"],
    "wind_gust_mps": ["hist_wind_gust_mps"],
    "temperature_c": ["hist_temperature_c"],
    "relative_humidity_pct": ["hist_relative_humidity_pct"],
    "pressure_hpa": ["hist_pressure_hpa"],
    "precipitation_mm": ["hist_precipitation_mm"],
    "air_density_kgm3": ["hist_air_density_kgm3"],
}


@dataclass
class WeatherToFlightFeatureAdapter:
    """把天气源数据转换为模型训练/推理共用的飞行分段特征。"""

    weather_source: str = "forecast_weather"
    feature_source: str = "weather_adapter"

    def transform(
        self,
        mission: MissionSpec,
        vehicle: VehicleSpec,
        weather_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """生成路线-时间序列特征表。"""

        return build_route_time_feature_frame(
            mission=mission,
            vehicle=vehicle,
            weather_frame=weather_frame,
            weather_source=self.weather_source,
            feature_source=self.feature_source,
        )


def _route_points_for_mission(mission: MissionSpec, vehicle: VehicleSpec) -> List[GeoPoint]:
    """生成用于分段的航线点。"""

    if len(mission.route_points) >= 2:
        return list(mission.route_points)

    total_distance_m = float(haversine_m(mission.start.lat, mission.start.lon, mission.end.lat, mission.end.lon))
    total_time_s = total_distance_m / float(vehicle.cruise_speed_mps)
    step_seconds = max(1, int(mission.step_minutes) * 60)
    point_count = max(2, int(np.ceil(total_time_s / step_seconds)) + 1)
    return build_route_points(mission.start, mission.end, point_count)


def _segment_altitude_m(start: GeoPoint, end: GeoPoint, vehicle: VehicleSpec) -> float:
    """优先使用显式航点高度，否则使用车辆巡航高度。"""

    altitudes = np.asarray([start.alt_m, end.alt_m], dtype=float)
    if np.isfinite(altitudes).any() and not np.allclose(np.nan_to_num(altitudes), 0.0):
        return float(np.nanmean(altitudes))
    return float(vehicle.altitude_m)


def _point_altitude_m(point: GeoPoint, vehicle: VehicleSpec) -> float:
    """读取航点高度，缺失或为 0 时回退到车辆巡航高度。"""

    altitude = float(point.alt_m)
    if np.isfinite(altitude) and not np.isclose(altitude, 0.0):
        return altitude
    return float(vehicle.altitude_m)


def _segment_altitude_features(start: GeoPoint, end: GeoPoint, vehicle: VehicleSpec, duration_s: float) -> dict:
    """由计划 3D 航线起终点高度生成垂直动态特征。"""

    start_alt = _point_altitude_m(start, vehicle)
    end_alt = _point_altitude_m(end, vehicle)
    delta = end_alt - start_alt
    vertical_speed = delta / duration_s if duration_s > 1e-9 else float("nan")
    abs_vertical_speed = abs(vertical_speed) if np.isfinite(vertical_speed) else float("nan")
    return {
        "altitude_start_m": start_alt,
        "altitude_end_m": end_alt,
        "altitude_delta_m": delta,
        "altitude_range_m": abs(delta),
        "altitude_gain_m": max(delta, 0.0),
        "altitude_loss_m": max(-delta, 0.0),
        "vertical_speed_mean_mps": vertical_speed,
        "vertical_speed_abs_mean_mps": abs_vertical_speed,
        "vertical_speed_abs_p95_mps": abs_vertical_speed,
    }


def _optional_weather_value(row: pd.Series, keys: Sequence[str]) -> float:
    """读取可选天气字段。"""

    return row_value(row, list(keys), default=np.nan)


def _first_numeric_series(frame: pd.DataFrame, candidates: Sequence[str]) -> pd.Series:
    """读取候选列中的第一个有效数值序列。"""

    for column in candidates:
        if column in frame.columns:
            return pd.to_numeric(frame[column], errors="coerce")
    return pd.Series([np.nan] * len(frame.index), index=frame.index, dtype=float)


def _fill_wind_components_from_weather(frame: pd.DataFrame) -> pd.DataFrame:
    """当历史天气没有直接逆风/侧风时，由风速风向和航向补算。"""

    if "heading_deg" not in frame.columns:
        return frame
    required = ["wind_speed_mps", "wind_dir_deg"]
    if not set(required).issubset(frame.columns):
        return frame

    missing_components = False
    for column in ["headwind_mps", "crosswind_mps"]:
        if column not in frame.columns or pd.to_numeric(frame[column], errors="coerce").notna().sum() == 0:
            missing_components = True
    if not missing_components:
        return frame

    wind_speed = pd.to_numeric(frame["wind_speed_mps"], errors="coerce")
    wind_dir = pd.to_numeric(frame["wind_dir_deg"], errors="coerce")
    heading = pd.to_numeric(frame["heading_deg"], errors="coerce")
    headwind = np.full(len(frame.index), np.nan, dtype=float)
    crosswind = np.full(len(frame.index), np.nan, dtype=float)
    valid = wind_speed.notna() & wind_dir.notna() & heading.notna()
    for idx in frame.index[valid]:
        one_headwind, one_crosswind = compute_wind_components(
            float(wind_speed.loc[idx]),
            float(wind_dir.loc[idx]),
            float(heading.loc[idx]),
        )
        headwind[frame.index.get_loc(idx)] = one_headwind
        crosswind[frame.index.get_loc(idx)] = one_crosswind
    if "headwind_mps" not in frame.columns:
        frame["headwind_mps"] = headwind
    else:
        frame["headwind_mps"] = pd.to_numeric(frame["headwind_mps"], errors="coerce").fillna(pd.Series(headwind, index=frame.index))
    if "crosswind_mps" not in frame.columns:
        frame["crosswind_mps"] = crosswind
    else:
        frame["crosswind_mps"] = pd.to_numeric(frame["crosswind_mps"], errors="coerce").fillna(pd.Series(crosswind, index=frame.index))
    return frame


def _circular_abs_delta_deg(values: pd.Series) -> pd.Series:
    """计算相邻航向的最小夹角变化。"""

    numeric = pd.to_numeric(values, errors="coerce")
    previous = numeric.shift(1)
    delta = ((numeric - previous + 180.0) % 360.0) - 180.0
    return delta.abs().fillna(0.0)


def _safe_haversine_from_row(start_lat, start_lon, end_lat, end_lon) -> float:
    """安全计算两点球面距离，缺失时返回 NaN。"""

    values = [start_lat, start_lon, end_lat, end_lon]
    if any(pd.isna(value) for value in values):
        return float("nan")
    return float(haversine_m(float(start_lat), float(start_lon), float(end_lat), float(end_lon)))


def _safe_bearing_from_row(start_lat, start_lon, end_lat, end_lon) -> float:
    """安全计算两点方位角，缺失时返回 NaN。"""

    values = [start_lat, start_lon, end_lat, end_lon]
    if any(pd.isna(value) for value in values):
        return float("nan")
    return float(bearing_deg(float(start_lat), float(start_lon), float(end_lat), float(end_lon)))


def add_route_geometry_features(frame: pd.DataFrame, group_col: str = "flight") -> pd.DataFrame:
    """补充可迁移的路线几何特征，避免模型只记住路线编号。"""

    out = frame.copy()
    for column in ROUTE_GEOMETRY_FEATURE_COLUMNS:
        if column not in out.columns:
            out[column] = np.nan

    if out.empty or "distance_m" not in out.columns or "heading_deg" not in out.columns:
        return out

    groups = out[group_col].fillna("__nan__").astype(str) if group_col in out.columns else pd.Series("__all__", index=out.index)
    for _, index_values in groups.groupby(groups, sort=False).groups.items():
        group_index = list(index_values)
        group = out.loc[group_index].copy()
        if group.empty:
            continue

        distance = pd.to_numeric(group["distance_m"], errors="coerce").fillna(0.0).clip(lower=0.0)
        total_distance_m = float(distance.sum())
        total_distance_km = total_distance_m / 1000.0 if total_distance_m > 1e-9 else np.nan
        cumulative_start_m = distance.cumsum() - distance
        route_progress_ratio = (
            (cumulative_start_m + distance / 2.0) / total_distance_m if total_distance_m > 1e-9 else pd.Series(np.nan, index=group.index)
        )
        route_remaining_distance_m = (total_distance_m - cumulative_start_m - distance).clip(lower=0.0)
        route_distance_share = distance / total_distance_m if total_distance_m > 1e-9 else pd.Series(np.nan, index=group.index)

        heading = pd.to_numeric(group["heading_deg"], errors="coerce")
        heading_rad = np.deg2rad(heading)
        heading_change = _circular_abs_delta_deg(heading)
        total_heading_change = float(heading_change.sum())
        segment_turn_density = heading_change / (distance / 1000.0).replace(0.0, np.nan)
        route_turn_density = total_heading_change / total_distance_km if np.isfinite(total_distance_km) and total_distance_km > 1e-9 else np.nan

        first = group.iloc[0]
        last = group.iloc[-1]
        direct_distance_m = float("nan")
        route_bearing = float("nan")
        if {"start_lat", "start_lon", "end_lat", "end_lon"}.issubset(group.columns):
            direct_distance_m = _safe_haversine_from_row(first["start_lat"], first["start_lon"], last["end_lat"], last["end_lon"])
            route_bearing = _safe_bearing_from_row(first["start_lat"], first["start_lon"], last["end_lat"], last["end_lon"])
        tortuosity = total_distance_m / direct_distance_m if np.isfinite(direct_distance_m) and direct_distance_m > 1e-9 else np.nan
        bearing_rad = np.deg2rad(route_bearing) if np.isfinite(route_bearing) else np.nan
        relative_heading = np.deg2rad(((heading - route_bearing + 180.0) % 360.0) - 180.0) if np.isfinite(route_bearing) else pd.Series(np.nan, index=group.index)

        altitude_values = []
        for column in ["altitude_start_m", "altitude_end_m", "altitude_m"]:
            if column in group.columns:
                altitude_values.append(pd.to_numeric(group[column], errors="coerce"))
        if altitude_values:
            altitude_all = pd.concat(altitude_values, axis=0).dropna()
            route_altitude_range = float(altitude_all.max() - altitude_all.min()) if not altitude_all.empty else np.nan
        else:
            route_altitude_range = np.nan

        if "altitude_gain_m" in group.columns:
            total_altitude_gain = float(pd.to_numeric(group["altitude_gain_m"], errors="coerce").fillna(0.0).clip(lower=0.0).sum())
        elif "altitude_delta_m" in group.columns:
            total_altitude_gain = float(pd.to_numeric(group["altitude_delta_m"], errors="coerce").fillna(0.0).clip(lower=0.0).sum())
        else:
            total_altitude_gain = np.nan

        if "altitude_loss_m" in group.columns:
            total_altitude_loss = float(pd.to_numeric(group["altitude_loss_m"], errors="coerce").fillna(0.0).clip(lower=0.0).sum())
        elif "altitude_delta_m" in group.columns:
            total_altitude_loss = float((-pd.to_numeric(group["altitude_delta_m"], errors="coerce").fillna(0.0).clip(upper=0.0)).sum())
        else:
            total_altitude_loss = np.nan

        climb_density = total_altitude_gain / total_distance_km if np.isfinite(total_altitude_gain) and np.isfinite(total_distance_km) and total_distance_km > 1e-9 else np.nan
        descent_density = total_altitude_loss / total_distance_km if np.isfinite(total_altitude_loss) and np.isfinite(total_distance_km) and total_distance_km > 1e-9 else np.nan

        out.loc[group.index, "heading_sin"] = np.sin(heading_rad)
        out.loc[group.index, "heading_cos"] = np.cos(heading_rad)
        out.loc[group.index, "route_direct_distance_m"] = direct_distance_m
        out.loc[group.index, "route_total_distance_m"] = total_distance_m
        out.loc[group.index, "route_tortuosity"] = tortuosity
        out.loc[group.index, "route_segment_count"] = int(len(group.index))
        out.loc[group.index, "route_progress_ratio"] = route_progress_ratio
        out.loc[group.index, "route_remaining_distance_m"] = route_remaining_distance_m
        out.loc[group.index, "route_distance_share"] = route_distance_share
        out.loc[group.index, "route_total_heading_change_deg"] = total_heading_change
        out.loc[group.index, "route_turn_density_deg_per_km"] = route_turn_density
        out.loc[group.index, "segment_heading_change_deg"] = heading_change
        out.loc[group.index, "segment_turn_density_deg_per_km"] = segment_turn_density
        out.loc[group.index, "route_bearing_deg"] = route_bearing
        out.loc[group.index, "route_bearing_sin"] = np.sin(bearing_rad) if np.isfinite(bearing_rad) else np.nan
        out.loc[group.index, "route_bearing_cos"] = np.cos(bearing_rad) if np.isfinite(bearing_rad) else np.nan
        out.loc[group.index, "segment_route_alignment"] = np.cos(relative_heading)
        out.loc[group.index, "segment_route_cross_alignment"] = np.sin(relative_heading)
        out.loc[group.index, "route_total_altitude_gain_m"] = total_altitude_gain
        out.loc[group.index, "route_total_altitude_loss_m"] = total_altitude_loss
        out.loc[group.index, "route_altitude_range_m"] = route_altitude_range
        out.loc[group.index, "route_climb_density_m_per_km"] = climb_density
        out.loc[group.index, "route_descent_density_m_per_km"] = descent_density

    return out


def build_preflight_training_feature_view(
    segment_frame: pd.DataFrame,
    weather_source: str = "historical_weather",
    feature_source: str = "preflight_training_view",
) -> pd.DataFrame:
    """把分段训练样本中的历史天气映射为运行时同名特征。"""

    out = segment_frame.copy()
    if "payload_kg" not in out.columns and "payload_g" in out.columns:
        out["payload_kg"] = pd.to_numeric(out["payload_g"], errors="coerce") / 1000.0
    out = ensure_planned_ground_speed(out)

    for target, candidates in PREFLIGHT_TRAINING_WEATHER_MAP.items():
        out[target] = _first_numeric_series(segment_frame, candidates)

    out = _fill_wind_components_from_weather(out)
    out = add_planned_equivalent_wind_features(out)
    geometry_group = "flight" if "flight" in out.columns else "route"
    out = add_route_geometry_features(out, group_col=geometry_group)
    out["feature_source"] = feature_source
    out["weather_source"] = weather_source
    return out


def build_route_time_feature_frame(
    mission: MissionSpec,
    vehicle: VehicleSpec,
    weather_frame: pd.DataFrame,
    weather_source: str = "forecast_weather",
    feature_source: str = "weather_adapter",
) -> pd.DataFrame:
    """把飞行前可得天气转换为沿航线分段展开的模型输入特征。"""

    if weather_frame.empty:
        raise ValueError("天气特征适配需要非空 weather_frame。")
    if vehicle.cruise_speed_mps <= 0:
        raise ValueError("巡航速度必须大于 0。")

    points = _route_points_for_mission(mission, vehicle)
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

    if not segment_specs:
        raise ValueError("航线没有可用分段。")

    target_times = pd.DatetimeIndex(
        [mission.departure_time + timedelta(seconds=spec["midpoint_s"]) for spec in segment_specs]
    )
    aligned_weather = interpolate_weather(weather_frame, target_times)

    rows = []
    for spec, (_, weather_row) in zip(segment_specs, aligned_weather.iterrows()):
        start = spec["start"]
        end = spec["end"]
        altitude_m = _segment_altitude_m(start, end, vehicle)
        heading_deg = float(bearing_deg(start.lat, start.lon, end.lat, end.lon))
        altitude_features = _segment_altitude_features(start, end, vehicle, float(spec["duration_s"]))
        wind_speed_mps, wind_dir_deg = height_aware_wind(weather_row, altitude_m)
        headwind_mps, crosswind_mps = compute_wind_components(wind_speed_mps, wind_dir_deg, heading_deg)

        temperature_c = _optional_weather_value(weather_row, ["temperature_c", "temp_c"])
        pressure_hpa = _optional_weather_value(weather_row, ["pressure_hpa", "pressure_msl_hpa"])
        relative_humidity_pct = _optional_weather_value(
            weather_row,
            ["relative_humidity_pct", "humidity_pct", "relative_humidity_2m"],
        )
        precipitation_mm = _optional_weather_value(weather_row, ["precipitation_mm", "precipitation"])
        wind_gust_mps = _optional_weather_value(weather_row, ["wind_gust_mps", "wind_gusts_10m"])

        air_density_kgm3 = float("nan")
        if np.isfinite(temperature_c) and np.isfinite(pressure_hpa):
            air_density_kgm3 = compute_air_density(temperature_c=temperature_c, pressure_hpa=pressure_hpa)

        start_time = mission.departure_time + timedelta(seconds=spec["elapsed_start_s"])
        end_time = mission.departure_time + timedelta(seconds=spec["elapsed_end_s"])
        mid_time = mission.departure_time + timedelta(seconds=spec["midpoint_s"])
        rows.append(
            {
                "route_name": mission.route_name,
                "segment_id": int(spec["segment_id"]),
                "feature_source": feature_source,
                "weather_source": weather_source,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "mid_time": mid_time.isoformat(),
                "elapsed_start_s": float(spec["elapsed_start_s"]),
                "elapsed_end_s": float(spec["elapsed_end_s"]),
                "start_lat": float(start.lat),
                "start_lon": float(start.lon),
                "end_lat": float(end.lat),
                "end_lon": float(end.lon),
                "planned_ground_speed_mps": float(vehicle.cruise_speed_mps),
                "speed_mps": float(vehicle.cruise_speed_mps),
                "payload_kg": float(vehicle.payload_g) / 1000.0,
                "altitude_m": altitude_m,
                **altitude_features,
                "distance_m": float(spec["distance_m"]),
                "duration_s": float(spec["duration_s"]),
                "heading_deg": heading_deg,
                "wind_speed_mps": float(wind_speed_mps),
                "wind_dir_deg": float(wind_dir_deg),
                "headwind_mps": float(headwind_mps),
                "crosswind_mps": float(crosswind_mps),
                "wind_gust_mps": float(wind_gust_mps),
                "temperature_c": float(temperature_c),
                "relative_humidity_pct": float(relative_humidity_pct),
                "pressure_hpa": float(pressure_hpa),
                "precipitation_mm": float(precipitation_mm),
                "air_density_kgm3": float(air_density_kgm3),
            }
        )

    frame = pd.DataFrame(rows)
    frame = add_planned_equivalent_wind_features(frame)
    frame = add_route_geometry_features(frame, group_col="route_name")
    return frame[[column for column in ROUTE_TIME_COLUMNS if column in frame.columns]]
