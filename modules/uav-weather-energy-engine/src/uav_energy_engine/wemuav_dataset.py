# 负责将 WEMUAV 多旋翼风估计数据集转换为引擎统一飞行日志格式。
"""负责将 WEMUAV 多旋翼风估计数据集整理为统一 flights.csv。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Union
import zipfile

import numpy as np
import pandas as pd

from .dataset import CANONICAL_FLIGHT_COLUMNS
from .utils import circular_mean_deg, ensure_dir


FLIGHT_COLUMN_ALIASES: Dict[str, Sequence[str]] = {
    "absolute_time": ["GPS:dateTimeStamp", "GPS(0):dateTimeStamp", "GPS_dateTimeStamp"],
    "offset_time": ["Clock:offsetTime", "offsetTime", "flightTime", "osd_data:flightTime"],
    "position_x": ["GPS:Long", "GPS(0):Long", "IMU_ATTI(0):Longitude"],
    "position_y": ["GPS:Lat", "GPS(0):Lat", "IMU_ATTI(0):Latitude"],
    "position_z": [
        "IMU_ATTI(0):relativeHeight:C",
        "General:relativeHeight",
        "GPS:heightMSL",
        "GPS(0):heightMSL",
        "IMU_ATTI(0):absoluteHeight:C",
        "General:absoluteHeight",
        "MVO:height",
    ],
    "speed": [
        "IMU_ATTI(0):velH:C",
        "IMU_ATTI(0):velH",
        "IMU_ATTI(0):velComposite:C",
        "IMU_ATTI(0):velComposite",
        "GPS:velH",
    ],
    "gps_vel_n": ["GPS:velN", "GPS(0):velN", "IMU_ATTI(0):velN"],
    "gps_vel_e": ["GPS:velE", "GPS(0):velE", "IMU_ATTI(0):velE"],
    "battery_voltage": ["BatteryInfo:BatVol:D", "BatteryInfo:Vol:D", "BattInfo:Pack_ve", "BattInfo:Ad_v", "BattInfo:vol_t"],
    "battery_current": [
        "BatteryInfo:BatCurrent:D",
        "BatteryInfo:Current:D",
        "BattInfo:Current",
        "BattInfo:AvgCurrent",
    ],
    "wind_speed": ["AirSpeed:windSpeed", "Wind:velocity"],
    "wind_angle": ["AirSpeed:windDirection", "AirSpeed:windFromDir", "Wind:fromDir", "Wind:direction"],
    "heading_deg": ["IMU_ATTI(0):yaw360", "IMU_ATTI(0):yaw:C", "IMU_ATTI(0):yaw"],
    "accel_x": ["IMU_ATTI(0):accelX", "IMU_ATTI(0):accel:X"],
    "accel_y": ["IMU_ATTI(0):accelY", "IMU_ATTI(0):accel:Y"],
    "accel_z": ["IMU_ATTI(0):accelZ", "IMU_ATTI(0):accel:Z"],
    "gyro_x": ["IMU_ATTI(0):gyroX", "IMU_ATTI(0):gyro:X"],
    "gyro_y": ["IMU_ATTI(0):gyroY", "IMU_ATTI(0):gyro:Y"],
    "gyro_z": ["IMU_ATTI(0):gyroZ", "IMU_ATTI(0):gyro:Z"],
}

WEMUAV_EXTRA_COLUMNS = [
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

TOPOAWS_COLUMNS = [
    "TOW",
    "AirTemp1",
    "AirHumidity",
    "AtmPressure",
    "WindSpeed",
    "WindDir",
    "GPSTime_Legacy",
    "Lati",
    "Long",
    "Alti",
    "GPSNbrSat",
    "GPSLockFlag",
    "TempCPU",
    "TempSens",
    "BattCharge",
    "FanOn",
]

CARDINAL_WIND_DEG = {
    "CIP": 0.0,
    "RC": 0.0,
    "N": 0.0,
    "NNE": 22.5,
    "NE": 45.0,
    "ENE": 67.5,
    "E": 90.0,
    "ESE": 112.5,
    "SE": 135.0,
    "SSE": 157.5,
    "S": 180.0,
    "SSW": 202.5,
    "SW": 225.0,
    "WSW": 247.5,
    "W": 270.0,
    "WNW": 292.5,
    "NW": 315.0,
    "NNW": 337.5,
}


def _all_aliases() -> list[str]:
    """汇总需要读取的原始飞行列名。"""

    aliases: list[str] = []
    for columns in FLIGHT_COLUMN_ALIASES.values():
        aliases.extend(columns)
    return aliases


def _naive_datetime(value) -> pd.Timestamp:
    """将输入时间解析为无时区 Timestamp。"""

    ts = pd.to_datetime(value, errors="coerce", dayfirst=True, format="mixed")
    if pd.isna(ts):
        return pd.NaT
    if getattr(ts, "tzinfo", None) is not None:
        return ts.tz_convert(None) if hasattr(ts, "tz_convert") else ts.tz_localize(None)
    return ts


def _naive_datetime_series(values: pd.Series) -> pd.Series:
    """将一列时间解析为无时区 datetime64。"""

    series = pd.to_datetime(values, errors="coerce", utc=True, dayfirst=True, format="mixed")
    if series.notna().any():
        return series.dt.tz_convert(None)
    series = pd.to_datetime(values, errors="coerce", dayfirst=True, format="mixed")
    if hasattr(series.dt, "tz_localize"):
        try:
            return series.dt.tz_localize(None)
        except TypeError:
            return series
    return series


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    """读取数值列，缺失时返回全 NaN。"""

    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _coalesce_numeric(frame: pd.DataFrame, candidates: Sequence[str]) -> pd.Series:
    """按候选列顺序做逐行空值回退。"""

    out = pd.Series(np.nan, index=frame.index, dtype=float)
    for column in candidates:
        if column not in frame.columns:
            continue
        out = out.fillna(pd.to_numeric(frame[column], errors="coerce"))
    return out


def _coalesce_numeric_with_source(frame: pd.DataFrame, candidates: Sequence[str]) -> tuple[pd.Series, pd.Series]:
    """按候选列顺序读取数值，并记录每行实际采用的源列。"""

    out = pd.Series(np.nan, index=frame.index, dtype=float)
    source = pd.Series(pd.NA, index=frame.index, dtype=object)
    for column in candidates:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        mask = out.isna() & values.notna()
        out.loc[mask] = values.loc[mask]
        source.loc[mask] = column
    return out, source


def _normalize_voltage_current_unit(values: pd.Series) -> pd.Series:
    """按数值量级把毫伏/毫安自动转换为伏/安。"""

    numeric = pd.to_numeric(values, errors="coerce")
    finite = numeric[np.isfinite(numeric)]
    if finite.empty:
        return numeric
    median_abs = float(finite.abs().median())
    if median_abs > 100.0:
        return numeric / 1000.0
    return numeric


def _read_zip_csv_columns(zip_path: Path, member: str) -> list[str]:
    """读取 zip 内 CSV 表头。"""

    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(member) as fh:
            return pd.read_csv(fh, nrows=0).columns.tolist()


def _read_zip_csv_selected(zip_path: Path, member: str, wanted_columns: Iterable[str]) -> pd.DataFrame:
    """只读取 zip 内 CSV 的候选列，避免把大日志整表载入内存。"""

    columns = _read_zip_csv_columns(zip_path, member)
    wanted = set(wanted_columns)
    usecols = [column for column in columns if column in wanted]
    if not usecols:
        raise ValueError(f"{member} 中未找到 WEMUAV 适配所需列。")
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(member) as fh:
            return pd.read_csv(fh, usecols=usecols, low_memory=False)


def _read_zip_weather(zip_path: Path, member: str) -> pd.DataFrame:
    """读取 WEMUAV 气象站 TOA5 风格天气文件。"""

    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(member) as fh:
            first_line = fh.readline().decode("utf-8", errors="replace").strip()
        if not first_line.startswith('"TOA5"'):
            with zf.open(member) as fh:
                weather = pd.read_csv(
                    fh,
                    sep=r"\s+",
                    header=None,
                    names=TOPOAWS_COLUMNS,
                    engine="python",
                )
            if weather.empty:
                return weather
            week_start = _naive_datetime(Path(member).stem)
            if pd.isna(week_start):
                weather["weather_time"] = pd.NaT
            else:
                weather["weather_time"] = week_start + pd.to_timedelta(
                    pd.to_numeric(weather["TOW"], errors="coerce"),
                    unit="s",
                )
            return weather.dropna(subset=["weather_time"]).copy()

        with zf.open(member) as fh:
            weather = pd.read_csv(fh, header=0, skiprows=[0, 2, 3], low_memory=False)
    if weather.empty:
        return weather

    time_col = weather.columns[0]
    weather = weather.rename(columns={time_col: "weather_time"})
    weather["weather_time"] = _naive_datetime_series(weather["weather_time"])
    weather = weather.dropna(subset=["weather_time"]).copy()
    return weather


def _wind_dir_degrees(values: pd.Series) -> pd.Series:
    """将数值或方位词风向统一转换为角度。"""

    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().all():
        return numeric
    mapped = values.astype(str).str.strip().str.upper().map(CARDINAL_WIND_DEG)
    return numeric.fillna(mapped)


def _source_archive(dataset_root: Path, folder: str) -> Path:
    """按文件夹名前缀找到对应飞行压缩包。"""

    prefix = "02_EPFL" if folder.startswith("EPFL") else "03_SVALBARD"
    candidates = sorted(dataset_root.glob(f"{prefix}*FLIGHTS.zip"))
    if not candidates:
        candidates = sorted(dataset_root.glob("*FLIGHTS.zip"))
    for candidate in candidates:
        with zipfile.ZipFile(candidate, "r") as zf:
            if any(name.startswith(f"{folder}/") for name in zf.namelist()):
                return candidate
    raise FileNotFoundError(f"未找到 WEMUAV 数据压缩包中的文件夹: {folder}")


def _segment_weather_summary(weather: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, fallback_wind) -> dict:
    """按任务时间窗汇总外部气象站天气。"""

    if weather.empty:
        segment = weather
    else:
        mask = (weather["weather_time"] >= start) & (weather["weather_time"] <= end)
        segment = weather.loc[mask].copy()
        if segment.empty:
            segment = weather.copy()

    summary = {
        "hist_wind_speed_mps": np.nan,
        "hist_wind_dir_deg": np.nan,
        "hist_wind_gust_mps": np.nan,
        "hist_temperature_c": np.nan,
        "hist_pressure_hpa": np.nan,
        "hist_relative_humidity_pct": np.nan,
        "hist_precipitation_mm": np.nan,
    }
    if segment.empty:
        summary["hist_wind_speed_mps"] = pd.to_numeric(pd.Series([fallback_wind]), errors="coerce").iloc[0]
        return summary

    if {"WindSpeed", "WindDir"}.issubset(segment.columns):
        wind_speed = pd.to_numeric(segment["WindSpeed"], errors="coerce")
        wind_dir = _wind_dir_degrees(segment["WindDir"])
        summary["hist_wind_speed_mps"] = float(wind_speed.mean())
        summary["hist_wind_gust_mps"] = float(wind_speed.max())
        summary["hist_wind_dir_deg"] = circular_mean_deg(wind_dir.to_numpy(dtype=float))
        summary["hist_temperature_c"] = float(_coalesce_numeric(segment, ["AirTemp1", "AirTemp"]).mean())
        summary["hist_pressure_hpa"] = float(_coalesce_numeric(segment, ["AtmPressure"]).mean())
        summary["hist_relative_humidity_pct"] = float(_coalesce_numeric(segment, ["AirHumidity"]).mean())
        return summary

    speed_columns = [column for column in ["VH1_sek", "VH2_sek"] if column in segment.columns]
    dir_columns = [column for column in ["VR1_sek", "VR2_sek"] if column in segment.columns]
    if speed_columns:
        speed_values = segment[speed_columns].apply(pd.to_numeric, errors="coerce")
        summary["hist_wind_speed_mps"] = float(speed_values.stack().mean())
        summary["hist_wind_gust_mps"] = float(speed_values.stack().max())
    if dir_columns:
        dir_values = segment[dir_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float).reshape(-1)
        summary["hist_wind_dir_deg"] = circular_mean_deg(dir_values)

    temp_columns = [column for column in ["LT1_sek", "LT2_sek", "LT3_sek", "LT4_sek"] if column in segment.columns]
    humid_columns = [column for column in ["LF1_sek", "LF2_sek"] if column in segment.columns]
    if temp_columns:
        summary["hist_temperature_c"] = float(segment[temp_columns].apply(pd.to_numeric, errors="coerce").stack().mean())
    if "AT_sek" in segment.columns:
        summary["hist_pressure_hpa"] = float(pd.to_numeric(segment["AT_sek"], errors="coerce").mean())
    if humid_columns:
        summary["hist_relative_humidity_pct"] = float(
            segment[humid_columns].apply(pd.to_numeric, errors="coerce").stack().mean()
        )
    if not np.isfinite(summary["hist_wind_speed_mps"]):
        summary["hist_wind_speed_mps"] = pd.to_numeric(pd.Series([fallback_wind]), errors="coerce").iloc[0]
    return summary


def _standardize_flight_frame(raw: pd.DataFrame, source_data_type: str) -> pd.DataFrame:
    """将 WEMUAV 原始飞行表转换为统一列。"""

    out = pd.DataFrame(index=raw.index)
    out["_absolute_time"] = _naive_datetime_series(_coalesce_text(raw, FLIGHT_COLUMN_ALIASES["absolute_time"]))
    out["_offset_time"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["offset_time"])
    out["position_x"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["position_x"])
    out["position_y"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["position_y"])
    out["position_z"], out["position_z_source_column"] = _coalesce_numeric_with_source(
        raw,
        FLIGHT_COLUMN_ALIASES["position_z"],
    )
    out["speed"], out["speed_source_column"] = _coalesce_numeric_with_source(raw, FLIGHT_COLUMN_ALIASES["speed"])

    if out["speed"].isna().all():
        vel_n = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["gps_vel_n"])
        vel_e = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["gps_vel_e"])
        out["speed"] = np.sqrt(np.square(vel_n) + np.square(vel_e))
        out["speed_source_column"] = "gps_vel_n/gps_vel_e"

    voltage_raw, out["battery_voltage_source_column"] = _coalesce_numeric_with_source(
        raw,
        FLIGHT_COLUMN_ALIASES["battery_voltage"],
    )
    current_raw, out["battery_current_source_column"] = _coalesce_numeric_with_source(
        raw,
        FLIGHT_COLUMN_ALIASES["battery_current"],
    )
    voltage = _normalize_voltage_current_unit(voltage_raw)
    current = _normalize_voltage_current_unit(current_raw)
    out["battery_voltage"] = voltage
    out["battery_current"] = current

    out["wind_speed"], out["wind_speed_source_column"] = _coalesce_numeric_with_source(
        raw,
        FLIGHT_COLUMN_ALIASES["wind_speed"],
    )
    out["wind_angle"], out["wind_angle_source_column"] = _coalesce_numeric_with_source(
        raw,
        FLIGHT_COLUMN_ALIASES["wind_angle"],
    )
    out["heading_deg"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["heading_deg"])
    out["accel_x"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["accel_x"])
    out["accel_y"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["accel_y"])
    out["accel_z"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["accel_z"])
    out["gyro_x"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["gyro_x"])
    out["gyro_y"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["gyro_y"])
    out["gyro_z"] = _coalesce_numeric(raw, FLIGHT_COLUMN_ALIASES["gyro_z"])
    out["ang_vel_x"] = out["gyro_x"]
    out["ang_vel_y"] = out["gyro_y"]
    out["ang_vel_z"] = out["gyro_z"]
    return out


def _coalesce_text(frame: pd.DataFrame, candidates: Sequence[str]) -> pd.Series:
    """按候选列顺序做文本空值回退。"""

    out = pd.Series(pd.NA, index=frame.index, dtype=object)
    for column in candidates:
        if column not in frame.columns:
            continue
        series = frame[column].where(frame[column].notna() & (frame[column].astype(str).str.len() > 0), pd.NA)
        out = out.fillna(series)
    return out


def _standardize_segment(
    flight_frame: pd.DataFrame,
    weather_summary: dict,
    row: pd.Series,
    start: pd.Timestamp,
    end: pd.Timestamp,
    flight_id_offset: int,
) -> pd.DataFrame:
    """按 overview 中的一条任务记录裁剪飞行段。"""

    if flight_frame["_absolute_time"].notna().any():
        mask = (flight_frame["_absolute_time"] >= start) & (flight_frame["_absolute_time"] <= end)
        segment = flight_frame.loc[mask].copy()
    else:
        segment = flight_frame.copy()
    if segment.empty:
        return segment

    offset_time = pd.to_numeric(segment["_offset_time"], errors="coerce")
    if offset_time.notna().any():
        first_time = float(offset_time.dropna().iloc[0])
        segment["time"] = offset_time - first_time
    else:
        first_abs_time = segment["_absolute_time"].dropna().iloc[0]
        segment["time"] = (segment["_absolute_time"] - first_abs_time).dt.total_seconds()

    case_id = int(pd.to_numeric(pd.Series([row["ID"]]), errors="coerce").iloc[0])
    flight_type = str(row.get("FlightType", "WEMUAV_UNKNOWN")).strip() or "WEMUAV_UNKNOWN"
    folder = str(row.get("FOLDER", "")).strip()
    flight_file = str(row.get("FLIGHT", "")).strip()
    weather_file = str(row.get("REFMETEO", "")).strip()
    source_data_type = str(row.get("FLIGHTDATATYPE", "")).strip()

    segment["flight"] = case_id + int(flight_id_offset)
    segment["local_time"] = start.strftime("%H:%M:%S")
    segment["payload"] = 0.0
    segment["altitude"] = segment["position_z"]
    segment["date"] = start.strftime("%Y-%m-%d")
    segment["route"] = flight_type
    segment["source_dataset"] = "wemuav"
    segment["source_case_id"] = case_id
    segment["source_folder"] = folder
    segment["source_flight_file"] = flight_file
    segment["source_weather_file"] = weather_file
    segment["source_flight_type"] = flight_type
    segment["source_data_type"] = source_data_type
    segment["altitude_source"] = segment["position_z_source_column"].fillna("missing").astype(str)
    segment["wind_speed_source"] = np.where(
        segment["wind_speed_source_column"].notna(),
        "flight_log:" + segment["wind_speed_source_column"].fillna("").astype(str),
        "missing",
    )
    segment["wind_angle_source"] = np.where(
        segment["wind_angle_source_column"].notna(),
        "flight_log:" + segment["wind_angle_source_column"].fillna("").astype(str),
        "missing",
    )
    segment["segment_start_time"] = start.isoformat()
    segment["segment_end_time"] = end.isoformat()

    for column, value in weather_summary.items():
        segment[column] = value

    # 将外部气象站字段同时填入当前天气列，保证旧训练入口也能使用。
    segment["temperature_c"] = weather_summary.get("hist_temperature_c", np.nan)
    segment["pressure_hpa"] = weather_summary.get("hist_pressure_hpa", np.nan)
    segment["relative_humidity_pct"] = weather_summary.get("hist_relative_humidity_pct", np.nan)
    segment["precipitation_mm"] = weather_summary.get("hist_precipitation_mm", np.nan)
    segment["wind_gust_mps"] = weather_summary.get("hist_wind_gust_mps", np.nan)

    if segment["wind_speed"].isna().all() and np.isfinite(weather_summary.get("hist_wind_speed_mps", np.nan)):
        segment["wind_speed"] = weather_summary["hist_wind_speed_mps"]
        segment["wind_speed_source"] = "external_weather"
    if segment["wind_angle"].isna().all() and np.isfinite(weather_summary.get("hist_wind_dir_deg", np.nan)):
        segment["wind_angle"] = weather_summary["hist_wind_dir_deg"]
        segment["wind_angle_source"] = "external_weather"

    return segment


def prepare_wemuav_dataset(
    dataset_root: Union[str, Path],
    output_csv: Union[str, Path],
    overview_csv: Optional[Union[str, Path]] = None,
    flight_id_offset: int = 1_000_000,
    max_cases: Optional[int] = None,
) -> pd.DataFrame:
    """将 WEMUAV 数据集整理为引擎统一的 flights.csv。"""

    dataset_root_path = Path(dataset_root)
    overview_path = Path(overview_csv) if overview_csv is not None else dataset_root_path / "01_DATA_OVERVIEW.csv"
    if not overview_path.exists():
        raise FileNotFoundError(f"未找到 WEMUAV overview: {overview_path}")

    overview = pd.read_csv(overview_path, encoding="utf-8-sig")
    overview.columns = [str(column).strip() for column in overview.columns]
    required = {"ID", "FOLDER", "FLIGHT", "DataStartTimeString", "DataEndTimeString"}
    missing = required - set(overview.columns)
    if missing:
        raise ValueError(f"WEMUAV overview 缺少字段: {sorted(missing)}")

    if max_cases is not None:
        overview = overview.head(int(max_cases)).copy()

    flight_cache: Dict[str, pd.DataFrame] = {}
    weather_cache: Dict[str, pd.DataFrame] = {}
    rows = []

    for _, row in overview.iterrows():
        start = _naive_datetime(row["DataStartTimeString"])
        end = _naive_datetime(row["DataEndTimeString"])
        if pd.isna(start) or pd.isna(end):
            continue

        folder = str(row["FOLDER"]).strip()
        flight_file = str(row["FLIGHT"]).strip()
        weather_file = str(row.get("REFMETEO", "")).strip()
        source_data_type = str(row.get("FLIGHTDATATYPE", "")).strip()
        archive = _source_archive(dataset_root_path, folder)
        flight_member = f"{folder}/FLIGHT/{flight_file}"
        weather_member = f"{folder}/WEATHER/{weather_file}" if weather_file and weather_file != "-" else ""

        flight_key = f"{archive}:{flight_member}"
        if flight_key not in flight_cache:
            raw_flight = _read_zip_csv_selected(archive, flight_member, _all_aliases())
            flight_cache[flight_key] = _standardize_flight_frame(raw_flight, source_data_type)

        fallback_wind = row.get("Mean windHMag [m/s]", np.nan)
        weather_summary = _segment_weather_summary(pd.DataFrame(), start, end, fallback_wind)
        if weather_member:
            weather_key = f"{archive}:{weather_member}"
            if weather_key not in weather_cache:
                try:
                    weather_cache[weather_key] = _read_zip_weather(archive, weather_member)
                except KeyError:
                    weather_cache[weather_key] = pd.DataFrame()
            weather_summary = _segment_weather_summary(weather_cache[weather_key], start, end, fallback_wind)

        segment = _standardize_segment(
            flight_frame=flight_cache[flight_key],
            weather_summary=weather_summary,
            row=row,
            start=start,
            end=end,
            flight_id_offset=flight_id_offset,
        )
        if not segment.empty:
            rows.append(segment)

    if not rows:
        raise ValueError("未从 WEMUAV 数据集中构建出任何有效飞行日志。")

    combined = pd.concat(rows, ignore_index=True)
    combined = combined.dropna(subset=["flight", "time", "battery_voltage", "battery_current"], how="any")
    combined = combined.sort_values(["flight", "time"]).reset_index(drop=True)

    ordered_columns = [
        column
        for column in CANONICAL_FLIGHT_COLUMNS
        + [
            "hist_wind_speed_mps",
            "hist_wind_dir_deg",
            "hist_wind_gust_mps",
            "hist_relative_humidity_pct",
            "hist_temperature_c",
            "hist_pressure_hpa",
            "hist_precipitation_mm",
        ]
        + WEMUAV_EXTRA_COLUMNS
        if column in combined.columns
    ]
    other_columns = [column for column in combined.columns if column not in ordered_columns and not column.startswith("_")]
    combined = combined[ordered_columns + other_columns]

    output_path = Path(output_csv)
    ensure_dir(output_path.parent)
    combined.to_csv(output_path, index=False)
    return combined
