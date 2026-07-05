# 负责从原始飞行日志构建训练样本表，并适配公开 M100 数据与历史天气回填结果。
"""负责从原始飞行日志构建训练样本表。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union
import tempfile
import zipfile
import re

import numpy as np
import pandas as pd

from .features import compute_air_density, enrich_flight_log_features
from .planned_equivalent_features import add_planned_equivalent_wind_features
from .utils import bearing_deg, circular_mean_deg, ensure_dir, haversine_m
from .weather import circular_interp_deg


SEGMENT_REQUIRED_COLUMNS = [
    "flight",
    "time",
    "wind_speed",
    "wind_angle",
    "battery_voltage",
    "battery_current",
    "position_x",
    "position_y",
    "position_z",
    "speed",
    "payload",
    "altitude",
    "date",
    "route",
]

SEGMENT_OPTIONAL_NUMERIC_COLUMNS = [
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
    "ang_vel_x",
    "ang_vel_y",
    "ang_vel_z",
    "heading_deg",
    "hist_wind_speed_mps",
    "hist_wind_dir_deg",
    "hist_wind_speed_100m_mps",
    "hist_wind_dir_100m_deg",
    "hist_wind_gust_mps",
    "hist_relative_humidity_pct",
    "hist_temperature_c",
    "hist_pressure_hpa",
    "hist_precipitation_mm",
    "relative_humidity_pct",
    "temperature_c",
    "pressure_hpa",
    "precipitation_mm",
    "wind_gust_mps",
]

SEGMENT_OPTIONAL_TEXT_COLUMNS = [
    "source_dataset",
    "source_case_id",
    "source_folder",
    "source_flight_file",
    "source_weather_file",
    "source_flight_type",
    "source_data_type",
    "altitude_source",
    "wind_speed_source",
    "wind_angle_source",
    "position_z_source_column",
    "speed_source_column",
    "battery_voltage_source_column",
    "battery_current_source_column",
    "wind_speed_source_column",
    "wind_angle_source_column",
    "segment_start_time",
    "segment_end_time",
]


CANONICAL_FLIGHT_COLUMNS = [
    "flight",
    "time",
    "local_time",
    "wind_speed",
    "wind_angle",
    "battery_voltage",
    "battery_current",
    "position_x",
    "position_y",
    "position_z",
    "speed",
    "payload",
    "altitude",
    "date",
    "route",
    "relative_humidity_pct",
    "temperature_c",
    "pressure_hpa",
    "precipitation_mm",
    "wind_gust_mps",
    "discharge_mah",
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
    "mag_x",
    "mag_y",
    "mag_z",
    "ang_vel_x",
    "ang_vel_y",
    "ang_vel_z",
    "ang_acc_x",
    "ang_acc_y",
    "ang_acc_z",
    "heading_deg",
]

M100_FLIGHT_ALIASES = {
    "time": ["time", "timestamp", "t", "elapsed_time", "duration"],
    "local_time": ["local_time", "time_day", "clock_time"],
    "wind_speed": ["wind_speed", "wind speed", "wind_velocity", "windspeed"],
    "wind_angle": ["wind_angle", "wind_direction", "wind direction", "wind_dir", "winddir"],
    "battery_voltage": ["battery_voltage", "voltage", "battery voltage"],
    "battery_current": ["battery_current", "current", "battery current"],
    "position_x": ["position_x", "x", "longitude", "lon"],
    "position_y": ["position_y", "y", "latitude", "lat"],
    "position_z": ["position_z", "altitude_sea_level", "altitude_msl", "msl_altitude"],
    "speed": ["speed", "planned_ground_speed_mps", "ground_speed", "velocity", "airspeed"],
    "altitude": ["altitude", "height", "alt"],
    "discharge_mah": ["discharge_mah", "discharge", "mah", "discharge_capacity"],
    "accel_x": ["accel_x", "ax", "acc_x", "linear_acceleration_x"],
    "accel_y": ["accel_y", "ay", "acc_y", "linear_acceleration_y"],
    "accel_z": ["accel_z", "az", "acc_z", "linear_acceleration_z"],
    "gyro_x": ["gyro_x", "gx", "angular_velocity_x", "gyroscope_x"],
    "gyro_y": ["gyro_y", "gy", "angular_velocity_y", "gyroscope_y"],
    "gyro_z": ["gyro_z", "gz", "angular_velocity_z", "gyroscope_z"],
    "mag_x": ["mag_x", "mx", "magnetic_field_x"],
    "mag_y": ["mag_y", "my", "magnetic_field_y"],
    "mag_z": ["mag_z", "mz", "magnetic_field_z"],
    "ang_vel_x": ["ang_vel_x", "omega_x", "body_rate_x"],
    "ang_vel_y": ["ang_vel_y", "omega_y", "body_rate_y"],
    "ang_vel_z": ["ang_vel_z", "omega_z", "body_rate_z"],
    "ang_acc_x": ["ang_acc_x", "angular_acceleration_x"],
    "ang_acc_y": ["ang_acc_y", "angular_acceleration_y"],
    "ang_acc_z": ["ang_acc_z", "angular_acceleration_z"],
    "heading_deg": ["heading_deg", "heading", "course", "course_deg", "yaw_deg"],
}

M100_PARAMETER_ALIASES = {
    "flight": ["flight", "id", "number", "flight_id"],
    "payload": ["payload", "payload_g", "payload mass", "payload_mass_g"],
    "speed": ["speed", "planned_ground_speed_mps", "speed_mps", "commanded_speed", "programmed_speed", "ground_speed_command"],
    "altitude": ["altitude", "altitude_m", "programmed_altitude", "commanded_altitude"],
    "route": ["route", "pattern", "flight_pattern"],
    "date": ["date", "datetime", "timestamp"],
    "local_time": ["local_time", "time_day", "clock_time"],
}


def _numeric_mean(group: pd.DataFrame, candidates) -> float:
    """返回候选列中的首个均值，若不存在则为 NaN。"""

    for column in candidates:
        if column in group.columns:
            return float(pd.to_numeric(group[column], errors="coerce").mean())
    return float("nan")


def _text_first(group: pd.DataFrame, column: str) -> Optional[str]:
    """读取分组内第一个非空文本值。"""

    if column not in group.columns:
        return None
    values = group[column].dropna().astype(str)
    values = values[values.str.len() > 0]
    if values.empty:
        return None
    return str(values.iloc[0])


def _numeric_stat(group: pd.DataFrame, column: str, stat: str) -> float:
    """计算数值列统计量，列不存在或全空时返回 NaN。"""

    if column not in group.columns:
        return float("nan")
    series = pd.to_numeric(group[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return float("nan")
    if stat == "mean":
        return float(series.mean())
    if stat == "max":
        return float(series.max())
    if stat == "min":
        return float(series.min())
    if stat == "std":
        return float(series.std(ddof=0))
    if stat == "p95":
        return float(series.quantile(0.95))
    raise ValueError(f"不支持的统计量: {stat}")


def _add_stats(row: Dict[str, float], group: pd.DataFrame, columns: Sequence[str]) -> None:
    """为一组列补充均值、最大值、标准差和 P95 统计。"""

    for column in columns:
        if column not in group.columns:
            continue
        row[f"{column}_mean"] = _numeric_stat(group, column, "mean")
        row[f"{column}_max"] = _numeric_stat(group, column, "max")
        row[f"{column}_std"] = _numeric_stat(group, column, "std")
        row[f"{column}_p95"] = _numeric_stat(group, column, "p95")


def _angle_diff_deg(current, previous) -> np.ndarray:
    """计算角度差，输出范围为 [-180, 180]。"""

    return (np.asarray(current, dtype=float) - np.asarray(previous, dtype=float) + 180.0) % 360.0 - 180.0


def _weighted_ratio(mask: np.ndarray, weights: np.ndarray) -> float:
    """按时长权重计算布尔条件占比。"""

    valid = np.isfinite(weights) & (weights > 0)
    if not valid.any():
        return float("nan")
    safe_mask = np.asarray(mask, dtype=bool) & valid
    return float(np.nansum(weights[safe_mask]) / np.nansum(weights[valid]))


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    """按时长权重计算均值。"""

    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not valid.any():
        return float("nan")
    return float(np.average(values[valid], weights=weights[valid]))


def _array_or_nan(group: pd.DataFrame, column: str) -> np.ndarray:
    """读取数值列，缺失时返回 NaN 数组。"""

    if column not in group.columns:
        return np.full(len(group.index), np.nan, dtype=float)
    return pd.to_numeric(group[column], errors="coerce").to_numpy(dtype=float)


def _dominant_phase(phase_ratios: Dict[str, float]) -> str:
    """选择占比最高的阶段标签。"""

    candidates = {
        "climb": phase_ratios.get("climb_ratio", np.nan),
        "descent": phase_ratios.get("descent_ratio", np.nan),
        "turn": phase_ratios.get("turn_ratio", np.nan),
        "hover_or_slow": phase_ratios.get("hover_or_slow_ratio", np.nan),
        "cruise": phase_ratios.get("cruise_ratio", np.nan),
    }
    valid = {key: value for key, value in candidates.items() if np.isfinite(value)}
    if not valid:
        return "unknown"
    return max(valid, key=valid.get)


def _compute_segment_phase_features(
    group: pd.DataFrame,
    time_s: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    seg_dist: np.ndarray,
    seg_bearing: np.ndarray,
    distance_m: float,
) -> Dict[str, float]:
    """从逐时刻轨迹推断分段阶段比例和物理动态特征。"""

    duration_s = float(time_s[-1] - time_s[0]) if len(time_s) >= 2 else float("nan")
    segment_horizontal_speed_mps = distance_m / duration_s if np.isfinite(duration_s) and duration_s > 1e-9 else float("nan")
    dt_step = np.diff(time_s)
    valid_dt = np.isfinite(dt_step) & (dt_step > 1e-9)
    z = _array_or_nan(group, "position_z")
    dz = np.diff(z)
    vertical_speed = np.full_like(dt_step, np.nan, dtype=float)
    vertical_speed[valid_dt] = dz[valid_dt] / dt_step[valid_dt]

    horizontal_speed = np.full_like(dt_step, np.nan, dtype=float)
    horizontal_speed[valid_dt] = np.asarray(seg_dist, dtype=float)[valid_dt] / dt_step[valid_dt]

    turn_rate = np.zeros_like(dt_step, dtype=float)
    if len(seg_bearing) >= 2:
        bearing_delta = np.abs(_angle_diff_deg(seg_bearing[1:], seg_bearing[:-1]))
        moving_step = valid_dt & np.isfinite(horizontal_speed) & (horizontal_speed > 0.5) & (np.asarray(seg_dist, dtype=float) > 0.3)
        valid_turn_dt = moving_step[1:] & moving_step[:-1] & np.isfinite(bearing_delta)
        turn_rate[1:][valid_turn_dt] = bearing_delta[valid_turn_dt] / dt_step[1:][valid_turn_dt]

    climb_threshold_mps = 0.3
    slow_threshold_mps = 0.7
    turn_threshold_deg_s = 20.0

    climb_mask = vertical_speed > climb_threshold_mps
    descent_mask = vertical_speed < -climb_threshold_mps
    level_mask = np.isfinite(vertical_speed) & (np.abs(vertical_speed) <= climb_threshold_mps)
    raw_slow_mask = np.isfinite(horizontal_speed) & (horizontal_speed < slow_threshold_mps)
    slow_mask = raw_slow_mask & np.isfinite(segment_horizontal_speed_mps) & (segment_horizontal_speed_mps < 1.5)
    turn_mask = np.isfinite(turn_rate) & (turn_rate > turn_threshold_deg_s) & np.isfinite(horizontal_speed) & (horizontal_speed > 1.0)
    cruise_mask = level_mask & (~slow_mask) & (~turn_mask)

    phase_ratios = {
        "climb_ratio": _weighted_ratio(climb_mask, dt_step),
        "descent_ratio": _weighted_ratio(descent_mask, dt_step),
        "level_ratio": _weighted_ratio(level_mask, dt_step),
        "turn_ratio": _weighted_ratio(turn_mask, dt_step),
        "hover_or_slow_ratio": _weighted_ratio(slow_mask, dt_step),
        "cruise_ratio": _weighted_ratio(cruise_mask, dt_step),
    }

    positive_dz = dz[np.isfinite(dz) & (dz > 0)]
    negative_dz = dz[np.isfinite(dz) & (dz < 0)]
    speed_delta = np.diff(horizontal_speed)
    accel_dt = dt_step[1:]
    accel = np.full_like(accel_dt, np.nan, dtype=float)
    valid_accel = np.isfinite(speed_delta) & np.isfinite(accel_dt) & (accel_dt > 1e-9)
    accel[valid_accel] = speed_delta[valid_accel] / accel_dt[valid_accel]

    gyro_z = _array_or_nan(group, "gyro_z")
    gyro_norm = np.sqrt(
        np.square(_array_or_nan(group, "gyro_x"))
        + np.square(_array_or_nan(group, "gyro_y"))
        + np.square(gyro_z)
    )
    accel_norm = np.sqrt(
        np.square(_array_or_nan(group, "accel_x"))
        + np.square(_array_or_nan(group, "accel_y"))
        + np.square(_array_or_nan(group, "accel_z"))
    )

    features: Dict[str, float] = {
        **phase_ratios,
        "phase_label": _dominant_phase(phase_ratios),
        "altitude_start_m": float(z[0]) if len(z) and np.isfinite(z[0]) else float("nan"),
        "altitude_end_m": float(z[-1]) if len(z) and np.isfinite(z[-1]) else float("nan"),
        "altitude_delta_m": float(z[-1] - z[0]) if len(z) and np.isfinite(z[0]) and np.isfinite(z[-1]) else float("nan"),
        "altitude_range_m": float(np.nanmax(z) - np.nanmin(z)) if np.isfinite(z).any() else float("nan"),
        "altitude_gain_m": float(np.nansum(positive_dz)) if positive_dz.size else 0.0,
        "altitude_loss_m": float(abs(np.nansum(negative_dz))) if negative_dz.size else 0.0,
        "vertical_speed_mean_mps": float((z[-1] - z[0]) / duration_s)
        if np.isfinite(duration_s) and duration_s > 1e-9 and len(z) and np.isfinite(z[0]) and np.isfinite(z[-1])
        else float("nan"),
        "vertical_speed_abs_mean_mps": _weighted_mean(np.abs(vertical_speed), dt_step),
        "vertical_speed_abs_p95_mps": float(np.nanpercentile(np.abs(vertical_speed[np.isfinite(vertical_speed)]), 95))
        if np.isfinite(vertical_speed).any()
        else float("nan"),
        "horizontal_speed_mean_mps": float(segment_horizontal_speed_mps),
        "horizontal_speed_std_mps": float(np.nanstd(horizontal_speed)) if np.isfinite(horizontal_speed).any() else float("nan"),
        "horizontal_speed_p95_mps": float(np.nanpercentile(horizontal_speed[np.isfinite(horizontal_speed)], 95))
        if np.isfinite(horizontal_speed).any()
        else float("nan"),
        "acceleration_abs_mean_mps2": float(np.nanmean(np.abs(accel))) if np.isfinite(accel).any() else float("nan"),
        "acceleration_abs_p95_mps2": float(np.nanpercentile(np.abs(accel[np.isfinite(accel)]), 95))
        if np.isfinite(accel).any()
        else float("nan"),
        "turn_rate_mean_deg_s": float(np.nanmean(turn_rate)) if np.isfinite(turn_rate).any() else float("nan"),
        "turn_rate_p95_deg_s": float(np.nanpercentile(turn_rate[np.isfinite(turn_rate)], 95))
        if np.isfinite(turn_rate).any()
        else float("nan"),
        "gyro_z_abs_mean": float(np.nanmean(np.abs(gyro_z))) if np.isfinite(gyro_z).any() else float("nan"),
        "gyro_norm_mean": float(np.nanmean(gyro_norm)) if np.isfinite(gyro_norm).any() else float("nan"),
        "accel_norm_mean": float(np.nanmean(accel_norm)) if np.isfinite(accel_norm).any() else float("nan"),
    }
    return features


def _prepare_feature_frame(input_csv: Union[str, Path], usecols: Sequence[str]) -> pd.DataFrame:
    """读取训练所需列并做基础数值化。"""

    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"输入数据不存在: {input_path}")

    available_columns = pd.read_csv(input_path, nrows=0).columns.tolist()
    df = pd.read_csv(
        input_path,
        usecols=[column for column in usecols if column in available_columns],
        low_memory=False,
    )
    text_columns = {"date", "route", "local_time", *SEGMENT_OPTIONAL_TEXT_COLUMNS}
    numeric_cols = [column for column in usecols if column in df.columns and column not in text_columns]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _canonicalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """将列名归一化，便于做宽松匹配。"""

    normalized = {}
    for column in frame.columns:
        normalized[column] = (
            str(column)
            .strip()
            .lower()
            .replace("(", "")
            .replace(")", "")
            .replace("[", "")
            .replace("]", "")
            .replace("/", "_")
            .replace("-", "_")
            .replace(" ", "_")
        )
    return frame.rename(columns=normalized)


def _first_present(frame: pd.DataFrame, candidates) -> Optional[str]:
    """在候选列名中找到第一个存在的列。"""

    for column in candidates:
        if column in frame.columns:
            return column
    return None


def _series_or_nan(frame: pd.DataFrame, column: Optional[str]) -> pd.Series:
    """读取列并转成数值，不存在则返回 NaN 序列。"""

    if column is None:
        return pd.Series([np.nan] * len(frame.index), index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _text_series_or_empty(frame: pd.DataFrame, column: Optional[str]) -> pd.Series:
    """读取文本列，不存在则返回空字符串序列。"""

    if column is None:
        return pd.Series([""] * len(frame.index), index=frame.index, dtype=object)
    return frame[column].fillna("").astype(str)


def _scalar_from_row(row: Optional[pd.Series], aliases, default=np.nan):
    """从参数行读取一个标量值。"""

    if row is None:
        return default
    for alias in aliases:
        if alias in row.index and pd.notna(row[alias]):
            return row[alias]
    return default


def _coerce_parameter_scalar(value, default=np.nan) -> float:
    """将参数表中的标量或剖面字符串收敛为数值。"""

    if value is None or (isinstance(value, float) and np.isnan(value)):
        return default
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = str(value).strip()
    if not text:
        return default

    try:
        return float(text)
    except ValueError:
        matches = re.findall(r"-?\d+(?:\.\d+)?", text)
        if not matches:
            return default
        # 对多段高度/速度剖面，当前阶段退化为首段标量，避免阻塞主链路。
        return float(matches[0])


def _load_parameters_frame(parameters_csv: Path) -> pd.DataFrame:
    """读取并规范化参数表。"""

    parameters = _canonicalize_columns(pd.read_csv(parameters_csv, low_memory=False))
    flight_col = _first_present(parameters, M100_PARAMETER_ALIASES["flight"])
    if flight_col is None:
        raise ValueError("参数表缺少 flight/id/number 列，无法匹配飞行编号。")
    parameters["flight"] = pd.to_numeric(parameters[flight_col], errors="coerce")
    parameters = parameters.dropna(subset=["flight"]).copy()
    parameters["flight"] = parameters["flight"].astype(int)
    return parameters


def _infer_flight_id_from_name(path: Path) -> Optional[int]:
    """从文件名中解析飞行编号。"""

    digits = "".join(ch for ch in path.stem if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _standardize_m100_flight_frame(flight_csv: Path, parameter_row: Optional[pd.Series]) -> pd.DataFrame:
    """将单个 M100 飞行 CSV 规范化到引擎通用格式。"""

    raw = _canonicalize_columns(pd.read_csv(flight_csv, low_memory=False))
    standardized = pd.DataFrame(index=raw.index)

    for canonical, aliases in M100_FLIGHT_ALIASES.items():
        source_col = _first_present(raw, aliases)
        if canonical == "local_time":
            standardized[canonical] = _text_series_or_empty(raw, source_col)
        else:
            standardized[canonical] = _series_or_nan(raw, source_col)

    flight_id = _infer_flight_id_from_name(flight_csv)
    if parameter_row is not None and "flight" in parameter_row.index and pd.notna(parameter_row["flight"]):
        flight_id = int(parameter_row["flight"])
    standardized["flight"] = flight_id

    payload_value = _scalar_from_row(parameter_row, M100_PARAMETER_ALIASES["payload"], default=np.nan)
    speed_value = _scalar_from_row(parameter_row, M100_PARAMETER_ALIASES["speed"], default=np.nan)
    altitude_value = _scalar_from_row(parameter_row, M100_PARAMETER_ALIASES["altitude"], default=np.nan)
    route_value = _scalar_from_row(parameter_row, M100_PARAMETER_ALIASES["route"], default="M100_TRIANGLE")
    date_value = _scalar_from_row(parameter_row, M100_PARAMETER_ALIASES["date"], default="")
    local_time_value = _scalar_from_row(parameter_row, M100_PARAMETER_ALIASES["local_time"], default="")

    standardized["payload"] = _coerce_parameter_scalar(payload_value)
    standardized["route"] = str(route_value) if pd.notna(route_value) else "M100_TRIANGLE"
    standardized["date"] = str(date_value) if pd.notna(date_value) else ""
    if standardized["local_time"].eq("").all():
        standardized["local_time"] = str(local_time_value) if pd.notna(local_time_value) else ""

    if standardized["speed"].isna().all():
        standardized["speed"] = _coerce_parameter_scalar(speed_value)
    if standardized["altitude"].isna().all():
        standardized["altitude"] = _coerce_parameter_scalar(altitude_value)

    for column in CANONICAL_FLIGHT_COLUMNS:
        if column not in standardized.columns:
            standardized[column] = np.nan

    return standardized[CANONICAL_FLIGHT_COLUMNS].copy()


def _extract_zip_to_temp(zip_path: Path) -> Path:
    """将 zip 临时解压到目录。"""

    temp_dir = Path(tempfile.mkdtemp(prefix="m100_flights_"))
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(temp_dir)
    return temp_dir


def aggregate_flight(group: pd.DataFrame) -> dict:
    """将单次飞行日志聚合为一条训练样本。"""

    group = group.sort_values("time").reset_index(drop=True)
    time_s = group["time"].to_numpy(dtype=float)
    dt = np.diff(time_s, prepend=time_s[0])
    dt[dt < 0] = 0.0

    voltage = group["battery_voltage"].to_numpy(dtype=float)
    current = np.abs(group["battery_current"].to_numpy(dtype=float))
    power_w = voltage * current
    energy_wh = np.nansum(power_w * dt) / 3600.0

    lat = group["position_y"].to_numpy(dtype=float)
    lon = group["position_x"].to_numpy(dtype=float)
    if len(lat) < 2:
        return {}

    seg_dist = haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
    distance_m = np.nansum(seg_dist)
    seg_bearing = bearing_deg(lat[:-1], lon[:-1], lat[1:], lon[1:])
    move_mask = seg_dist > 0.1
    heading = circular_mean_deg(seg_bearing[move_mask], weights=seg_dist[move_mask])
    phase_features = _compute_segment_phase_features(
        group=group,
        time_s=time_s,
        lat=lat,
        lon=lon,
        seg_dist=seg_dist,
        seg_bearing=seg_bearing,
        distance_m=distance_m,
    )

    wind_speed = float(np.nanmean(group["wind_speed"].to_numpy(dtype=float)))
    wind_dir = circular_mean_deg(group["wind_angle"].to_numpy(dtype=float))

    headwind = float("nan")
    crosswind = float("nan")
    if not np.isnan(heading) and not np.isnan(wind_dir):
        rel = np.deg2rad((wind_dir - heading) % 360.0)
        headwind = wind_speed * np.cos(rel)
        crosswind = wind_speed * np.sin(rel)

    hist_wind_speed = _numeric_mean(group, ["hist_wind_speed_mps", "hist_wind_speed"])
    hist_wind_dir = float("nan")
    if "hist_wind_dir_deg" in group.columns:
        hist_wind_dir = circular_mean_deg(
            pd.to_numeric(group["hist_wind_dir_deg"], errors="coerce").to_numpy(dtype=float)
        )
    hist_headwind = float("nan")
    hist_crosswind = float("nan")
    if not np.isnan(heading) and not np.isnan(hist_wind_dir) and np.isfinite(hist_wind_speed):
        rel = np.deg2rad((hist_wind_dir - heading) % 360.0)
        hist_headwind = hist_wind_speed * np.cos(rel)
        hist_crosswind = hist_wind_speed * np.sin(rel)

    temperature_c = _numeric_mean(group, ["temperature_c", "barometric_temperature", "temperature", "temp_c"])
    pressure_hpa = _numeric_mean(group, ["pressure_hpa", "barometric_pressure", "pressure", "pressure_mbar"])
    precipitation_mm = _numeric_mean(group, ["precipitation_mm", "precipitation", "tp"])
    wind_gust_mps = _numeric_mean(group, ["wind_gust_mps", "gust", "fg10"])
    relative_humidity_pct = _numeric_mean(group, ["relative_humidity_pct", "humidity", "rh", "rh2m"])
    hist_temperature_c = _numeric_mean(group, ["hist_temperature_c"])
    hist_pressure_hpa = _numeric_mean(group, ["hist_pressure_hpa"])
    hist_precipitation_mm = _numeric_mean(group, ["hist_precipitation_mm"])
    hist_wind_gust_mps = _numeric_mean(group, ["hist_wind_gust_mps"])
    hist_relative_humidity_pct = _numeric_mean(group, ["hist_relative_humidity_pct"])
    air_density_kgm3 = float("nan")
    if np.isfinite(temperature_c) and np.isfinite(pressure_hpa):
        air_density_kgm3 = compute_air_density(temperature_c=temperature_c, pressure_hpa=pressure_hpa)
    hist_air_density_kgm3 = float("nan")
    if np.isfinite(hist_temperature_c) and np.isfinite(hist_pressure_hpa):
        hist_air_density_kgm3 = compute_air_density(
            temperature_c=hist_temperature_c,
            pressure_hpa=hist_pressure_hpa,
        )

    planned_ground_speed_mps = float(np.nanmedian(group["speed"].to_numpy(dtype=float)))

    return {
        "flight": int(group["flight"].iloc[0]),
        "route": str(group["route"].iloc[0]),
        "date": str(group["date"].iloc[0]),
        "planned_ground_speed_mps": planned_ground_speed_mps,
        "speed_mps": planned_ground_speed_mps,
        "payload_g": float(np.nanmedian(group["payload"].to_numpy(dtype=float))),
        "altitude_m": float(np.nanmedian(group["altitude"].to_numpy(dtype=float))),
        "wind_speed_mps": wind_speed,
        "wind_dir_deg": wind_dir,
        "headwind_mps": headwind,
        "crosswind_mps": crosswind,
        "wind_gust_mps": wind_gust_mps,
        "hist_wind_speed_mps": hist_wind_speed,
        "hist_wind_dir_deg": hist_wind_dir,
        "hist_headwind_mps": hist_headwind,
        "hist_crosswind_mps": hist_crosswind,
        "hist_wind_gust_mps": hist_wind_gust_mps,
        "heading_deg": heading,
        "relative_humidity_pct": relative_humidity_pct,
        "temperature_c": temperature_c,
        "pressure_hpa": pressure_hpa,
        "precipitation_mm": precipitation_mm,
        "air_density_kgm3": air_density_kgm3,
        "hist_relative_humidity_pct": hist_relative_humidity_pct,
        "hist_temperature_c": hist_temperature_c,
        "hist_pressure_hpa": hist_pressure_hpa,
        "hist_precipitation_mm": hist_precipitation_mm,
        "hist_air_density_kgm3": hist_air_density_kgm3,
        "distance_m": distance_m,
        "energy_wh": energy_wh,
        "flight_time_s": float(time_s[-1] - time_s[0]),
    }


def build_training_dataset(
    input_csv: Union[str, Path],
    output_csv: Union[str, Path],
    route: Optional[str] = None,
) -> pd.DataFrame:
    """将 flights.csv 构建为训练样本表。"""

    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"输入数据不存在: {input_path}")

    usecols = [
        "flight",
        "time",
        "wind_speed",
        "wind_angle",
        "battery_voltage",
        "battery_current",
        "position_x",
        "position_y",
        "speed",
        "payload",
        "altitude",
        "hist_wind_speed_mps",
        "hist_wind_dir_deg",
        "hist_wind_gust_mps",
        "hist_relative_humidity_pct",
        "hist_temperature_c",
        "hist_pressure_hpa",
        "hist_precipitation_mm",
        "relative_humidity_pct",
        "temperature_c",
        "barometric_temperature",
        "temperature",
        "temp_c",
        "pressure_hpa",
        "barometric_pressure",
        "pressure",
        "pressure_mbar",
        "precipitation_mm",
        "precipitation",
        "tp",
        "wind_gust_mps",
        "gust",
        "fg10",
        "date",
        "route",
    ]
    available_columns = pd.read_csv(input_path, nrows=0).columns.tolist()
    df = pd.read_csv(
        input_path,
        usecols=[column for column in usecols if column in available_columns],
        low_memory=False,
    )
    numeric_cols = [
        "flight",
        "time",
        "wind_speed",
        "wind_angle",
        "battery_voltage",
        "battery_current",
        "position_x",
        "position_y",
        "speed",
        "payload",
        "altitude",
        "hist_wind_speed_mps",
        "hist_wind_dir_deg",
        "hist_wind_gust_mps",
        "hist_relative_humidity_pct",
        "hist_temperature_c",
        "hist_pressure_hpa",
        "hist_precipitation_mm",
        "relative_humidity_pct",
        "temperature_c",
        "barometric_temperature",
        "temperature",
        "temp_c",
        "pressure_hpa",
        "barometric_pressure",
        "pressure",
        "pressure_mbar",
        "precipitation_mm",
        "precipitation",
        "tp",
        "wind_gust_mps",
        "gust",
        "fg10",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if route:
        df = df[df["route"] == route]

    rows = []
    for _, group in df.groupby("flight"):
        row = aggregate_flight(group)
        if not row:
            continue
        if row["distance_m"] < 10.0 or row["flight_time_s"] < 10.0:
            continue
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("未构建出有效训练样本。")

    out["energy_wh_per_km"] = out["energy_wh"] / (out["distance_m"] / 1000.0)
    out = add_planned_equivalent_wind_features(out)
    output_path = Path(output_csv)
    ensure_dir(output_path.parent)
    out.to_csv(output_path, index=False)
    return out


def aggregate_segment(group: pd.DataFrame, segment_id: int, segment_start_s: float, segment_seconds: float) -> dict:
    """将单个飞行分段聚合为训练样本。"""

    group = group.sort_values("time").reset_index(drop=True)
    if len(group.index) < 2:
        return {}

    time_s = group["time"].to_numpy(dtype=float)
    dt = np.diff(time_s, prepend=time_s[0])
    dt[dt < 0] = 0.0

    voltage = group["battery_voltage"].to_numpy(dtype=float)
    current = np.abs(group["battery_current"].to_numpy(dtype=float))
    power_w = voltage * current
    segment_energy_wh = float(np.nansum(power_w * dt) / 3600.0)

    lat = group["position_y"].to_numpy(dtype=float)
    lon = group["position_x"].to_numpy(dtype=float)
    seg_dist = haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
    distance_m = float(np.nansum(seg_dist))
    if distance_m <= 0.0:
        return {}

    seg_bearing = bearing_deg(lat[:-1], lon[:-1], lat[1:], lon[1:])
    move_mask = seg_dist > 0.1
    heading = circular_mean_deg(seg_bearing[move_mask], weights=seg_dist[move_mask])
    phase_features = _compute_segment_phase_features(
        group=group,
        time_s=time_s,
        lat=lat,
        lon=lon,
        seg_dist=seg_dist,
        seg_bearing=seg_bearing,
        distance_m=distance_m,
    )

    wind_speed = float(np.nanmean(group["wind_speed"].to_numpy(dtype=float)))
    wind_dir = circular_mean_deg(group["wind_angle"].to_numpy(dtype=float))
    headwind = float("nan")
    crosswind = float("nan")
    if not np.isnan(heading) and not np.isnan(wind_dir):
        rel = np.deg2rad((wind_dir - heading) % 360.0)
        headwind = wind_speed * np.cos(rel)
        crosswind = wind_speed * np.sin(rel)

    hist_wind_speed = _numeric_mean(group, ["hist_wind_speed_mps"])
    hist_wind_dir = float("nan")
    if "hist_wind_dir_deg" in group.columns:
        hist_wind_dir = circular_mean_deg(
            pd.to_numeric(group["hist_wind_dir_deg"], errors="coerce").to_numpy(dtype=float)
        )
    hist_wind_speed_100m = _numeric_mean(group, ["hist_wind_speed_100m_mps"])
    hist_wind_dir_100m = float("nan")
    if "hist_wind_dir_100m_deg" in group.columns:
        hist_wind_dir_100m = circular_mean_deg(
            pd.to_numeric(group["hist_wind_dir_100m_deg"], errors="coerce").to_numpy(dtype=float)
        )
    altitude_m = float(np.nanmedian(group["altitude"].to_numpy(dtype=float)))
    hist_height_wind_speed = hist_wind_speed
    hist_height_wind_dir = hist_wind_dir
    if (
        np.isfinite(hist_wind_speed)
        and np.isfinite(hist_wind_dir)
        and np.isfinite(hist_wind_speed_100m)
        and np.isfinite(hist_wind_dir_100m)
    ):
        height_frac = float(np.clip((altitude_m - 10.0) / 90.0, 0.0, 1.0))
        hist_height_wind_speed = hist_wind_speed * (1.0 - height_frac) + hist_wind_speed_100m * height_frac
        hist_height_wind_dir = circular_interp_deg(hist_wind_dir, hist_wind_dir_100m, height_frac)
    hist_headwind = float("nan")
    hist_crosswind = float("nan")
    if not np.isnan(heading) and not np.isnan(hist_height_wind_dir) and np.isfinite(hist_height_wind_speed):
        rel = np.deg2rad((hist_height_wind_dir - heading) % 360.0)
        hist_headwind = hist_height_wind_speed * np.cos(rel)
        hist_crosswind = hist_height_wind_speed * np.sin(rel)

    hist_temperature_c = _numeric_mean(group, ["hist_temperature_c"])
    hist_pressure_hpa = _numeric_mean(group, ["hist_pressure_hpa"])
    hist_air_density_kgm3 = float("nan")
    if np.isfinite(hist_temperature_c) and np.isfinite(hist_pressure_hpa):
        hist_air_density_kgm3 = compute_air_density(
            temperature_c=hist_temperature_c,
            pressure_hpa=hist_pressure_hpa,
        )

    duration_s = float(time_s[-1] - time_s[0])
    segment_wh_per_s = segment_energy_wh / duration_s if duration_s > 0.0 else float("nan")
    mean_power_w = segment_energy_wh * 3600.0 / duration_s if duration_s > 0.0 else float("nan")

    planned_ground_speed_mps = float(np.nanmedian(group["speed"].to_numpy(dtype=float)))

    row: Dict[str, float] = {
        "flight": int(group["flight"].iloc[0]),
        "segment_id": int(segment_id),
        "route": str(group["route"].iloc[0]),
        "date": str(group["date"].iloc[0]),
        "segment_start_s": float(segment_start_s),
        "segment_end_s": float(segment_start_s + segment_seconds),
        "duration_s": duration_s,
        "start_lat": float(lat[0]),
        "start_lon": float(lon[0]),
        "end_lat": float(lat[-1]),
        "end_lon": float(lon[-1]),
        "heading_deg": heading,
        "distance_m": distance_m,
        "segment_energy_wh": segment_energy_wh,
        "segment_wh_per_s": segment_wh_per_s,
        "mean_power_w": mean_power_w,
        "segment_wh_per_km": segment_energy_wh / (distance_m / 1000.0),
        "planned_ground_speed_mps": planned_ground_speed_mps,
        "speed_mps": planned_ground_speed_mps,
        "payload_g": float(np.nanmedian(group["payload"].to_numpy(dtype=float))),
        "altitude_m": altitude_m,
        "wind_speed_mps": wind_speed,
        "wind_dir_deg": wind_dir,
        "headwind_mps": headwind,
        "crosswind_mps": crosswind,
        "hist_wind_speed_mps": hist_wind_speed,
        "hist_wind_dir_deg": hist_wind_dir,
        "hist_wind_speed_100m_mps": hist_wind_speed_100m,
        "hist_wind_dir_100m_deg": hist_wind_dir_100m,
        "hist_height_wind_speed_mps": hist_height_wind_speed,
        "hist_height_wind_dir_deg": hist_height_wind_dir,
        "hist_headwind_mps": hist_headwind,
        "hist_crosswind_mps": hist_crosswind,
        "hist_wind_gust_mps": _numeric_mean(group, ["hist_wind_gust_mps"]),
        "hist_relative_humidity_pct": _numeric_mean(group, ["hist_relative_humidity_pct"]),
        "hist_temperature_c": hist_temperature_c,
        "hist_pressure_hpa": hist_pressure_hpa,
        "hist_precipitation_mm": _numeric_mean(group, ["hist_precipitation_mm"]),
        "hist_air_density_kgm3": hist_air_density_kgm3,
        **phase_features,
    }
    for column in SEGMENT_OPTIONAL_TEXT_COLUMNS:
        value = _text_first(group, column)
        if value is not None:
            row[column] = value
    _add_stats(
        row,
        group,
        [
            "wind_speed",
            "hist_wind_speed_mps",
            "hist_wind_speed_100m_mps",
            "hist_wind_gust_mps",
            "hist_relative_humidity_pct",
            "hist_temperature_c",
            "hist_pressure_hpa",
            "hist_precipitation_mm",
        ],
    )
    return row


def build_segment_dataset(
    input_csv: Union[str, Path],
    output_csv: Union[str, Path],
    route: Optional[str] = None,
    segment_seconds: float = 60.0,
    min_distance_m: float = 50.0,
    min_duration_s: float = 10.0,
) -> pd.DataFrame:
    """将逐时刻飞行日志构建为分段级能耗样本。"""

    if segment_seconds <= 0:
        raise ValueError("segment_seconds 必须大于 0。")

    usecols = SEGMENT_REQUIRED_COLUMNS + SEGMENT_OPTIONAL_NUMERIC_COLUMNS + SEGMENT_OPTIONAL_TEXT_COLUMNS
    df = _prepare_feature_frame(input_csv, usecols)
    if route and "route" in df.columns:
        df = df[df["route"] == route].copy()

    rows: List[dict] = []
    for _, flight_group in df.groupby("flight"):
        flight_group = flight_group.sort_values("time").copy()
        if flight_group.empty:
            continue
        min_time = float(pd.to_numeric(flight_group["time"], errors="coerce").min())
        relative_time = pd.to_numeric(flight_group["time"], errors="coerce") - min_time
        segment_ids = np.floor(relative_time / float(segment_seconds)).astype("Int64")
        flight_group = flight_group.assign(segment_id=segment_ids)
        for segment_id, segment_group in flight_group.groupby("segment_id"):
            if pd.isna(segment_id):
                continue
            segment_start_s = float(int(segment_id) * segment_seconds)
            row = aggregate_segment(segment_group, int(segment_id), segment_start_s, segment_seconds)
            if not row:
                continue
            if row["distance_m"] < min_distance_m or row["duration_s"] < min_duration_s:
                continue
            rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("未构建出有效分段样本。")
    out = add_planned_equivalent_wind_features(out)

    output_path = Path(output_csv)
    ensure_dir(output_path.parent)
    out.to_csv(output_path, index=False)
    return out


def filter_segment_outliers(
    frame: pd.DataFrame,
    target_col: str = "segment_wh_per_km",
    min_target: Optional[float] = None,
    max_target: Optional[float] = None,
    lower_quantile: Optional[float] = None,
    upper_quantile: Optional[float] = None,
) -> tuple[pd.DataFrame, dict]:
    """按能耗目标过滤分段异常值，并返回过滤统计。"""

    if target_col not in frame.columns:
        raise ValueError(f"分段异常过滤缺少目标列: {target_col}")

    values = pd.to_numeric(frame[target_col], errors="coerce")
    mask = values.notna() & np.isfinite(values)
    lower_bound = min_target
    upper_bound = max_target
    if lower_quantile is not None:
        lower_bound = float(values[mask].quantile(lower_quantile))
    if upper_quantile is not None:
        upper_bound = float(values[mask].quantile(upper_quantile))
    if lower_bound is not None:
        mask &= values >= float(lower_bound)
    if upper_bound is not None:
        mask &= values <= float(upper_bound)

    filtered = frame.loc[mask].copy()
    meta = {
        "target_col": target_col,
        "rows_before": int(len(frame.index)),
        "rows_after": int(len(filtered.index)),
        "rows_removed": int(len(frame.index) - len(filtered.index)),
        "min_target": lower_bound,
        "max_target": upper_bound,
    }
    return filtered, meta


def build_research_feature_table(
    input_csv: Union[str, Path],
    output_csv: Union[str, Path],
    route: Optional[str] = None,
) -> pd.DataFrame:
    """构建更贴近论文复现的逐时刻研究特征表。"""

    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"输入数据不存在: {input_path}")

    frame = pd.read_csv(input_path, low_memory=False)
    if route and "route" in frame.columns:
        frame = frame[frame["route"] == route].copy()

    # 尽量把看起来像数值的列转成数值，保留 route/date 等文本列。
    skip_columns = {"route", "date", "time_iso", "timestamp_iso", "notes"}
    for column in frame.columns:
        if column in skip_columns:
            continue
        frame[column] = pd.to_numeric(frame[column], errors="ignore")

    enriched = enrich_flight_log_features(frame)
    if "discharge" in enriched.columns and "discharge_mah" not in enriched.columns:
        enriched["discharge_mah"] = pd.to_numeric(enriched["discharge"], errors="coerce")
    if "battery_voltage" in enriched.columns:
        enriched["battery_voltage"] = pd.to_numeric(enriched["battery_voltage"], errors="coerce")
    if "battery_current" in enriched.columns:
        enriched["battery_current"] = pd.to_numeric(enriched["battery_current"], errors="coerce")

    output_path = Path(output_csv)
    ensure_dir(output_path.parent)
    enriched.to_csv(output_path, index=False)
    return enriched


def prepare_m100_dataset(
    dataset_root: Union[str, Path],
    output_csv: Union[str, Path],
    flights_zip: Optional[Union[str, Path]] = None,
    parameters_csv: Optional[Union[str, Path]] = None,
    flight_id_offset: int = 0,
) -> pd.DataFrame:
    """将公开 M100 数据集整理为引擎统一的 flights.csv。"""

    dataset_root_path = Path(dataset_root)
    parameters_path = Path(parameters_csv) if parameters_csv is not None else dataset_root_path / "parameters.csv"
    if not parameters_path.exists():
        raise FileNotFoundError(f"未找到参数表: {parameters_path}")

    parameters = _load_parameters_frame(parameters_path)

    if flights_zip is not None:
        flights_source = Path(flights_zip)
    else:
        zip_candidates = sorted(dataset_root_path.glob("**/flights.zip"))
        flights_source = zip_candidates[0] if zip_candidates else dataset_root_path / "flights.zip"
    if not flights_source.exists():
        raise FileNotFoundError(f"未找到 flights.zip: {flights_source}")

    extract_root = _extract_zip_to_temp(flights_source)
    try:
        flight_csvs = sorted(extract_root.rglob("*.csv"))
        if not flight_csvs:
            raise ValueError("flights.zip 中未找到任何飞行 CSV。")

        rows = []
        for flight_csv in flight_csvs:
            flight_id = _infer_flight_id_from_name(flight_csv)
            parameter_row = None
            if flight_id is not None:
                matched = parameters[parameters["flight"] == flight_id]
                if not matched.empty:
                    parameter_row = matched.iloc[0]
            standardized = _standardize_m100_flight_frame(flight_csv, parameter_row)
            if standardized["flight"].notna().all() and int(flight_id_offset) != 0:
                standardized["flight"] = pd.to_numeric(standardized["flight"], errors="coerce") + int(flight_id_offset)
            rows.append(standardized)

        combined = pd.concat(rows, ignore_index=True)
        combined = combined.dropna(subset=["flight", "time", "battery_voltage", "battery_current"], how="any")
        combined["flight"] = combined["flight"].astype(int)

        output_path = Path(output_csv)
        ensure_dir(output_path.parent)
        combined.to_csv(output_path, index=False)
        return combined
    finally:
        # 临时解压目录没有长期价值，直接清掉。
        for path in sorted(extract_root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        extract_root.rmdir()
