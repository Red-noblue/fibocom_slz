# 定义天气与任务条件下的核心特征工程。
"""定义天气与任务条件下的核心特征工程。"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


ROUTE_FEATURE_COLUMNS = [
    "planned_ground_speed_mps",
    "speed_mps",
    "payload_kg",
    "altitude_m",
    "distance_m",
    "duration_s",
    "wind_speed_mps",
    "headwind_mps",
    "crosswind_mps",
]

DIRECT_WEATHER_MODEL_COLUMNS = [
    "wind_gust_mps",
    "temperature_c",
    "relative_humidity_pct",
    "pressure_hpa",
    "precipitation_mm",
    "air_density_kgm3",
    "hist_wind_speed_mps",
    "hist_wind_speed_100m_mps",
    "hist_height_wind_speed_mps",
    "hist_headwind_mps",
    "hist_crosswind_mps",
    "hist_wind_gust_mps",
    "hist_relative_humidity_pct",
    "hist_temperature_c",
    "hist_pressure_hpa",
    "hist_precipitation_mm",
    "hist_air_density_kgm3",
    "equivalent_airspeed_mps",
    "equivalent_along_track_airspeed_mps",
    "equivalent_cross_track_airspeed_mps",
    "equivalent_crosswind_abs_mps",
    "headwind_ratio",
    "crosswind_ratio",
    "tailwind_mps",
]

THESIS_WEATHER_FEATURE_COLUMNS = [
    "wind_speed_mps",
    "wind_dir_deg",
    "wind_gust_mps",
    "precipitation_mm",
    "pressure_hpa",
    "temperature_c",
    "geopotential_m",
]

THESIS_SENSOR_FEATURE_COLUMNS = [
    "derived_gps_distance_m",
    "normalized_timestamp",
    "gyro_magnitude_xyz",
    "magnetic_field_magnitude_xyz",
    "acceleration_magnitude_xyz",
    "vehicle_angular_acceleration",
    "vehicle_angular_velocity",
]

THESIS_TARGET_COLUMNS = [
    "battery_voltage",
    "battery_current",
    "discharge_mah",
]


def compute_air_density(temperature_c: float, pressure_hpa: float) -> float:
    """根据温度与气压估算空气密度。"""

    return float((pressure_hpa * 100.0) / (287.05 * (temperature_c + 273.15)))


def compute_wind_components(
    wind_speed_mps: float,
    wind_dir_deg: float,
    heading_deg: float,
) -> Tuple[float, float]:
    """根据风速、风向和航向计算逆风与侧风分量。"""

    rel = np.deg2rad((wind_dir_deg - heading_deg) % 360.0)
    headwind = wind_speed_mps * np.cos(rel)
    crosswind = wind_speed_mps * np.sin(rel)
    return float(headwind), float(crosswind)


def ensure_planned_ground_speed(frame: pd.DataFrame) -> pd.DataFrame:
    """统一计划地速字段，同时保留 speed_mps 兼容旧模型和旧脚本。"""

    out = frame.copy()
    if "planned_ground_speed_mps" not in out.columns and "speed_mps" in out.columns:
        out["planned_ground_speed_mps"] = pd.to_numeric(out["speed_mps"], errors="coerce")
    if "speed_mps" not in out.columns and "planned_ground_speed_mps" in out.columns:
        out["speed_mps"] = pd.to_numeric(out["planned_ground_speed_mps"], errors="coerce")
    return out


def compute_vector_magnitude(x_values, y_values, z_values) -> np.ndarray:
    """计算三轴向量模长。"""

    x_arr = np.asarray(x_values, dtype=float)
    y_arr = np.asarray(y_values, dtype=float)
    z_arr = np.asarray(z_values, dtype=float)
    return np.sqrt(np.square(x_arr) + np.square(y_arr) + np.square(z_arr))


def compute_geopotential_m(altitude_m: float) -> float:
    """根据海拔近似计算位势高度。"""

    earth_radius_m = 6_371_000.0
    altitude = float(altitude_m)
    return float((earth_radius_m * altitude) / (earth_radius_m + altitude))


def compute_normalized_timestamp(values: Sequence[float]) -> np.ndarray:
    """将时间戳序列归一化到 0 到 1。"""

    series = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    if series.size == 0:
        return np.asarray([], dtype=float)

    valid_mask = np.isfinite(series)
    normalized = np.full(series.shape, np.nan, dtype=float)
    if not valid_mask.any():
        return normalized

    valid_values = series[valid_mask]
    min_value = float(valid_values.min())
    max_value = float(valid_values.max())
    if max_value <= min_value:
        normalized[valid_mask] = 0.0
        return normalized

    normalized[valid_mask] = (valid_values - min_value) / (max_value - min_value)
    return normalized


def compute_derived_gps_distance(
    lat_values: Sequence[float],
    lon_values: Sequence[float],
    alt_values: Sequence[float],
) -> np.ndarray:
    """按论文思路将经纬高转为地心坐标后计算相邻点距离。"""

    lat_rad = np.deg2rad(np.asarray(lat_values, dtype=float))
    lon_rad = np.deg2rad(np.asarray(lon_values, dtype=float))
    alt_arr = np.asarray(alt_values, dtype=float)

    earth_radius_m = 6_371_000.0
    radius = earth_radius_m + alt_arr
    x_coord = radius * np.cos(lat_rad) * np.cos(lon_rad)
    y_coord = radius * np.cos(lat_rad) * np.sin(lon_rad)
    z_coord = radius * np.sin(lat_rad)

    ecef = np.column_stack([x_coord, y_coord, z_coord])
    if ecef.shape[0] == 0:
        return np.asarray([], dtype=float)
    if ecef.shape[0] == 1:
        return np.asarray([0.0], dtype=float)

    deltas = np.linalg.norm(np.diff(ecef, axis=0), axis=1)
    return np.concatenate([[0.0], deltas])


def _first_existing(frame: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    """在候选列名中找到第一个存在的列。"""

    for column in candidates:
        if column in frame.columns:
            return column
    return None


def _maybe_numeric(frame: pd.DataFrame, candidates: Iterable[str]) -> Optional[pd.Series]:
    """读取候选列中的第一个数值列。"""

    column = _first_existing(frame, candidates)
    if column is None:
        return None
    return pd.to_numeric(frame[column], errors="coerce")


def _ensure_heading(frame: pd.DataFrame) -> Optional[pd.Series]:
    """优先读取已有航向；若缺失则尝试由轨迹推导航向。"""

    heading = _maybe_numeric(frame, ["heading_deg", "heading", "course_deg", "course"])
    if heading is not None:
        return heading

    lat_series = _maybe_numeric(frame, ["lat", "latitude", "position_y"])
    lon_series = _maybe_numeric(frame, ["lon", "longitude", "position_x"])
    if lat_series is None or lon_series is None or len(frame.index) < 2:
        return None

    lat_arr = lat_series.to_numpy(dtype=float)
    lon_arr = lon_series.to_numpy(dtype=float)
    heading_arr = np.full(len(frame.index), np.nan, dtype=float)
    lat1 = np.deg2rad(lat_arr[:-1])
    lat2 = np.deg2rad(lat_arr[1:])
    dlon = np.deg2rad(lon_arr[1:] - lon_arr[:-1])
    y_val = np.sin(dlon) * np.cos(lat2)
    x_val = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
    heading_arr[1:] = (np.rad2deg(np.arctan2(y_val, x_val)) + 360.0) % 360.0
    if len(heading_arr) > 1:
        heading_arr[0] = heading_arr[1]
    return pd.Series(heading_arr, index=frame.index)


def enrich_flight_log_features(frame: pd.DataFrame, flight_col: str = "flight") -> pd.DataFrame:
    """为逐时刻飞行日志补充论文复现需要的派生特征。"""

    enriched = frame.copy()

    if "payload_kg" not in enriched.columns:
        payload_series = _maybe_numeric(enriched, ["payload_kg", "payload_g", "payload"])
        if payload_series is not None:
            payload_max = payload_series.max(skipna=True)
            if pd.notna(payload_max) and float(payload_max) > 50.0:
                enriched["payload_kg"] = payload_series / 1000.0
            else:
                enriched["payload_kg"] = payload_series

    altitude_series = _maybe_numeric(enriched, ["altitude_m", "altitude", "height_m"])
    if altitude_series is not None:
        if "altitude_m" not in enriched.columns:
            enriched["altitude_m"] = altitude_series
        if "geopotential_m" not in enriched.columns:
            enriched["geopotential_m"] = altitude_series.apply(
                lambda value: compute_geopotential_m(value) if pd.notna(value) else np.nan
            )

    pressure_series = _maybe_numeric(
        enriched,
        ["pressure_hpa", "barometric_pressure", "pressure", "pressure_mbar"],
    )
    if pressure_series is not None and "pressure_hpa" not in enriched.columns:
        enriched["pressure_hpa"] = pressure_series

    temperature_series = _maybe_numeric(
        enriched,
        ["temperature_c", "barometric_temperature", "temperature", "temp_c"],
    )
    if temperature_series is not None and "temperature_c" not in enriched.columns:
        enriched["temperature_c"] = temperature_series

    if pressure_series is not None and temperature_series is not None and "air_density_kgm3" not in enriched.columns:
        density_series = pd.Series(np.nan, index=enriched.index, dtype=float)
        valid_mask = pressure_series.notna() & temperature_series.notna()
        density_series.loc[valid_mask] = [
            compute_air_density(temp_value, pressure_value)
            for temp_value, pressure_value in zip(
                temperature_series.loc[valid_mask].to_numpy(dtype=float),
                pressure_series.loc[valid_mask].to_numpy(dtype=float),
            )
        ]
        enriched["air_density_kgm3"] = density_series

    wind_speed_series = _maybe_numeric(enriched, ["wind_speed_mps", "wind_speed", "ws10"])
    if wind_speed_series is not None and "wind_speed_mps" not in enriched.columns:
        enriched["wind_speed_mps"] = wind_speed_series

    wind_dir_series = _maybe_numeric(enriched, ["wind_dir_deg", "wind_angle", "wind_direction", "wd10"])
    if wind_dir_series is not None and "wind_dir_deg" not in enriched.columns:
        enriched["wind_dir_deg"] = wind_dir_series

    wind_gust_series = _maybe_numeric(enriched, ["wind_gust_mps", "gust", "fg10"])
    if wind_gust_series is not None and "wind_gust_mps" not in enriched.columns:
        enriched["wind_gust_mps"] = wind_gust_series

    if "normalized_timestamp" not in enriched.columns:
        time_column = _first_existing(enriched, ["time", "timestamp", "time_s"])
        if time_column is not None:
            if flight_col in enriched.columns:
                normalized_parts = []
                for _, group in enriched.groupby(flight_col, sort=False):
                    values = compute_normalized_timestamp(group[time_column].to_numpy(dtype=float))
                    normalized_parts.append(pd.Series(values, index=group.index))
                if normalized_parts:
                    enriched["normalized_timestamp"] = (
                        pd.concat(normalized_parts).sort_index().reindex(enriched.index)
                    )
            else:
                enriched["normalized_timestamp"] = compute_normalized_timestamp(
                    enriched[time_column].to_numpy(dtype=float)
                )

    lat_series = _maybe_numeric(enriched, ["lat", "latitude", "position_y"])
    lon_series = _maybe_numeric(enriched, ["lon", "longitude", "position_x"])
    if lat_series is not None and lon_series is not None and altitude_series is not None:
        if "derived_gps_distance_m" not in enriched.columns:
            if flight_col in enriched.columns:
                distance_parts = []
                for _, group in enriched.groupby(flight_col, sort=False):
                    distances = compute_derived_gps_distance(
                        lat_series.loc[group.index].to_numpy(dtype=float),
                        lon_series.loc[group.index].to_numpy(dtype=float),
                        altitude_series.loc[group.index].to_numpy(dtype=float),
                    )
                    distance_parts.append(pd.Series(distances, index=group.index))
                if distance_parts:
                    enriched["derived_gps_distance_m"] = (
                        pd.concat(distance_parts).sort_index().reindex(enriched.index)
                    )
            else:
                enriched["derived_gps_distance_m"] = compute_derived_gps_distance(
                    lat_series.to_numpy(dtype=float),
                    lon_series.to_numpy(dtype=float),
                    altitude_series.to_numpy(dtype=float),
                )

    heading_series = _ensure_heading(enriched)
    if (
        heading_series is not None
        and wind_speed_series is not None
        and wind_dir_series is not None
        and ("headwind_mps" not in enriched.columns or "crosswind_mps" not in enriched.columns)
    ):
        headwind = np.full(len(enriched.index), np.nan, dtype=float)
        crosswind = np.full(len(enriched.index), np.nan, dtype=float)
        valid_mask = wind_speed_series.notna() & wind_dir_series.notna() & heading_series.notna()
        if valid_mask.any():
            headwind_values = []
            crosswind_values = []
            for speed_value, dir_value, heading_value in zip(
                wind_speed_series.loc[valid_mask].to_numpy(dtype=float),
                wind_dir_series.loc[valid_mask].to_numpy(dtype=float),
                heading_series.loc[valid_mask].to_numpy(dtype=float),
            ):
                one_headwind, one_crosswind = compute_wind_components(speed_value, dir_value, heading_value)
                headwind_values.append(one_headwind)
                crosswind_values.append(one_crosswind)
            headwind[valid_mask.to_numpy()] = np.asarray(headwind_values, dtype=float)
            crosswind[valid_mask.to_numpy()] = np.asarray(crosswind_values, dtype=float)
        if "headwind_mps" not in enriched.columns:
            enriched["headwind_mps"] = headwind
        if "crosswind_mps" not in enriched.columns:
            enriched["crosswind_mps"] = crosswind

    for prefix in ["hist"]:
        prefixed_speed = _maybe_numeric(enriched, [f"{prefix}_wind_speed_mps", f"{prefix}_wind_speed"])
        prefixed_dir = _maybe_numeric(enriched, [f"{prefix}_wind_dir_deg", f"{prefix}_wind_angle"])
        if (
            heading_series is not None
            and prefixed_speed is not None
            and prefixed_dir is not None
            and (
                f"{prefix}_headwind_mps" not in enriched.columns
                or f"{prefix}_crosswind_mps" not in enriched.columns
            )
        ):
            headwind = np.full(len(enriched.index), np.nan, dtype=float)
            crosswind = np.full(len(enriched.index), np.nan, dtype=float)
            valid_mask = prefixed_speed.notna() & prefixed_dir.notna() & heading_series.notna()
            if valid_mask.any():
                headwind_values = []
                crosswind_values = []
                for speed_value, dir_value, heading_value in zip(
                    prefixed_speed.loc[valid_mask].to_numpy(dtype=float),
                    prefixed_dir.loc[valid_mask].to_numpy(dtype=float),
                    heading_series.loc[valid_mask].to_numpy(dtype=float),
                ):
                    one_headwind, one_crosswind = compute_wind_components(speed_value, dir_value, heading_value)
                    headwind_values.append(one_headwind)
                    crosswind_values.append(one_crosswind)
                headwind[valid_mask.to_numpy()] = np.asarray(headwind_values, dtype=float)
                crosswind[valid_mask.to_numpy()] = np.asarray(crosswind_values, dtype=float)
            if f"{prefix}_headwind_mps" not in enriched.columns:
                enriched[f"{prefix}_headwind_mps"] = headwind
            if f"{prefix}_crosswind_mps" not in enriched.columns:
                enriched[f"{prefix}_crosswind_mps"] = crosswind

        prefixed_pressure = _maybe_numeric(enriched, [f"{prefix}_pressure_hpa"])
        prefixed_temperature = _maybe_numeric(enriched, [f"{prefix}_temperature_c"])
        prefixed_density_col = f"{prefix}_air_density_kgm3"
        if (
            prefixed_pressure is not None
            and prefixed_temperature is not None
            and prefixed_density_col not in enriched.columns
        ):
            density_series = pd.Series(np.nan, index=enriched.index, dtype=float)
            valid_mask = prefixed_pressure.notna() & prefixed_temperature.notna()
            density_series.loc[valid_mask] = [
                compute_air_density(temp_value, pressure_value)
                for temp_value, pressure_value in zip(
                    prefixed_temperature.loc[valid_mask].to_numpy(dtype=float),
                    prefixed_pressure.loc[valid_mask].to_numpy(dtype=float),
                )
            ]
            enriched[prefixed_density_col] = density_series

    magnitude_specs = [
        ("gyro_magnitude_xyz", ["gyro_x", "gyro_y", "gyro_z"]),
        ("magnetic_field_magnitude_xyz", ["mag_x", "mag_y", "mag_z"]),
        ("acceleration_magnitude_xyz", ["accel_x", "accel_y", "accel_z"]),
        ("vehicle_angular_acceleration", ["ang_acc_x", "ang_acc_y", "ang_acc_z"]),
        ("vehicle_angular_velocity", ["ang_vel_x", "ang_vel_y", "ang_vel_z"]),
    ]
    for target_column, axis_columns in magnitude_specs:
        if target_column in enriched.columns:
            continue
        if not set(axis_columns).issubset(set(enriched.columns)):
            continue
        enriched[target_column] = compute_vector_magnitude(
            enriched[axis_columns[0]].to_numpy(dtype=float),
            enriched[axis_columns[1]].to_numpy(dtype=float),
            enriched[axis_columns[2]].to_numpy(dtype=float),
        )

    return enriched


def build_model_feature_row(
    speed_mps: float,
    payload_g: float,
    altitude_m: float,
    wind_speed_mps: float,
    wind_dir_deg: float,
    heading_deg: float,
    wind_gust_mps: Optional[float] = None,
    temperature_c: Optional[float] = None,
    relative_humidity_pct: Optional[float] = None,
    pressure_hpa: Optional[float] = None,
    precipitation_mm: Optional[float] = None,
    air_density_kgm3: Optional[float] = None,
) -> Dict[str, float]:
    """构建模型预测需要的一行输入特征。"""

    headwind, crosswind = compute_wind_components(wind_speed_mps, wind_dir_deg, heading_deg)
    planned_speed = float(speed_mps)
    equivalent_along_track = planned_speed + headwind
    speed_denom = abs(planned_speed) if abs(planned_speed) > 1e-9 else np.nan
    row = {
        "planned_ground_speed_mps": float(speed_mps),
        "speed_mps": float(speed_mps),
        "payload_kg": float(payload_g) / 1000.0,
        "altitude_m": float(altitude_m),
        "wind_speed_mps": float(wind_speed_mps),
        "wind_dir_deg": float(wind_dir_deg),
        "headwind_mps": headwind,
        "crosswind_mps": crosswind,
        "equivalent_airspeed_mps": float(np.hypot(equivalent_along_track, crosswind)),
        "equivalent_along_track_airspeed_mps": float(equivalent_along_track),
        "equivalent_cross_track_airspeed_mps": float(crosswind),
        "equivalent_crosswind_abs_mps": float(abs(crosswind)),
        "headwind_ratio": float(headwind / speed_denom) if np.isfinite(speed_denom) else np.nan,
        "crosswind_ratio": float(abs(crosswind) / speed_denom) if np.isfinite(speed_denom) else np.nan,
        "tailwind_mps": float(max(-headwind, 0.0)),
        "phase_is_climb": 0.0,
        "phase_is_descent": 0.0,
        "phase_is_level": 1.0,
        "phase_is_turn": 0.0,
        "phase_is_hover_or_slow": 0.0,
        "phase_is_cruise": 1.0,
    }
    if wind_gust_mps is not None and np.isfinite(wind_gust_mps):
        row["wind_gust_mps"] = float(wind_gust_mps)
    if temperature_c is not None and np.isfinite(temperature_c):
        row["temperature_c"] = float(temperature_c)
    if relative_humidity_pct is not None and np.isfinite(relative_humidity_pct):
        row["relative_humidity_pct"] = float(relative_humidity_pct)
    if pressure_hpa is not None and np.isfinite(pressure_hpa):
        row["pressure_hpa"] = float(pressure_hpa)
    if precipitation_mm is not None and np.isfinite(precipitation_mm):
        row["precipitation_mm"] = float(precipitation_mm)
    if air_density_kgm3 is not None and np.isfinite(air_density_kgm3):
        row["air_density_kgm3"] = float(air_density_kgm3)
    return row


def compute_weather_factor(
    temperature_c: float,
    relative_humidity_pct: float,
    pressure_hpa: float,
    precipitation_mm: float,
    visibility_km: float,
    uv_index: float,
    air_quality_index: float,
) -> float:
    """根据天气条件计算额外能耗修正因子。"""

    weather_factor = 1.0
    weather_factor += 0.006 * max(0.0, abs(temperature_c - 22.0) - 4.0)
    weather_factor += 0.030 * min(max(precipitation_mm, 0.0), 3.0)
    weather_factor += 0.0015 * max(0.0, relative_humidity_pct - 70.0)
    weather_factor += 0.0012 * max(0.0, 1013.25 - pressure_hpa)
    weather_factor += 0.0025 * max(0.0, 8.0 - visibility_km)
    weather_factor += 0.0010 * max(0.0, uv_index - 6.0)
    weather_factor += 0.0008 * max(0.0, air_quality_index - 80.0)
    return float(np.clip(weather_factor, 0.85, 1.75))


def to_frame(row: Dict[str, float]) -> pd.DataFrame:
    """将单行特征包装为 DataFrame。"""

    return pd.DataFrame([row])
