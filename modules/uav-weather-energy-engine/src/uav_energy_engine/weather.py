# 提供天气数据接入、时间对齐、空间插值和高度层风场估算。
"""提供天气数据接入、时间对齐和天气派生量估算。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import requests

from .config import load_config
from .schema import GeoPoint


class WeatherConfigError(Exception):
    """天气配置异常。"""


def _parse_path(path: str):
    tokens = []
    buf = ""
    idx = 0
    while idx < len(path):
        ch = path[idx]
        if ch == ".":
            if buf:
                tokens.append(buf)
                buf = ""
            idx += 1
            continue
        if ch == "[":
            if buf:
                tokens.append(buf)
                buf = ""
            end = path.find("]", idx)
            if end == -1:
                raise WeatherConfigError(f"无效路径表达式: {path}")
            tokens.append(int(path[idx + 1 : end]))
            idx = end + 1
            continue
        buf += ch
        idx += 1
    if buf:
        tokens.append(buf)
    return tokens


def extract_path(data: Any, path: str):
    """从嵌套对象中按路径提取字段。"""

    cur = data
    for token in _parse_path(path):
        if isinstance(token, int):
            if not isinstance(cur, list):
                raise WeatherConfigError(f"路径要求 list，但实际不是: {path}")
            if token >= len(cur):
                raise WeatherConfigError(f"路径索引越界: {path}")
            cur = cur[token]
        else:
            if not isinstance(cur, dict):
                raise WeatherConfigError(f"路径要求 dict，但实际不是: {path}")
            if token not in cur:
                raise WeatherConfigError(f"缺少字段 {token}: {path}")
            cur = cur[token]
    return cur


def apply_template(value: Any, mapping: Dict[str, str]):
    """替换模板字符串中的变量。"""

    if not isinstance(value, str):
        return value
    out = value
    for key, item in mapping.items():
        out = out.replace("{" + key + "}", item)
    return out


def normalize_field(values, scale: float, offset: float):
    """对接口返回字段做线性缩放。"""

    if isinstance(values, list):
        series = pd.to_numeric(pd.Series(values), errors="coerce")
        return (series * scale + offset).tolist()
    numeric = pd.to_numeric(pd.Series([values]), errors="coerce").iloc[0]
    return [float(numeric) * scale + offset]


class GenericWeatherClient:
    """配置驱动的天气接口客户端。"""

    def __init__(self, config_path: Union[str, Path]) -> None:
        self.config = load_config(config_path)

    def fetch_hourly(
        self,
        point: GeoPoint,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """拉取单点逐小时天气。"""

        base_url = self.config.get("base_url")
        if not base_url:
            raise WeatherConfigError("天气配置缺少 base_url")

        template = {
            "lat": str(point.lat),
            "lon": str(point.lon),
        }
        params = {
            key: apply_template(value, template)
            for key, value in (self.config.get("params") or {}).items()
        }
        if extra_params:
            for key, value in extra_params.items():
                if value is None:
                    params.pop(key, None)
                else:
                    params[key] = apply_template(value, template)

        headers = {
            key: apply_template(value, template)
            for key, value in (self.config.get("headers") or {}).items()
        }

        method = str(self.config.get("method", "GET")).upper()
        if method == "GET":
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
        else:
            response = requests.post(base_url, json=params, headers=headers, timeout=30)

        response.raise_for_status()
        payload = response.json()

        time_spec = self.config.get("time")
        if not time_spec or "path" not in time_spec:
            raise WeatherConfigError("天气配置缺少 time.path")
        time_values = extract_path(payload, time_spec["path"])
        time_values = time_values if isinstance(time_values, list) else [time_values]
        if time_spec.get("epoch_unit"):
            times = pd.to_datetime(time_values, unit=time_spec["epoch_unit"], utc=True)
        elif time_spec.get("format"):
            times = pd.to_datetime(time_values, format=time_spec["format"], errors="coerce")
        else:
            times = pd.to_datetime(time_values, errors="coerce")

        fields = self.config.get("fields")
        if not fields:
            raise WeatherConfigError("天气配置缺少 fields")

        data: Dict[str, list] = {}
        for name, spec in fields.items():
            if isinstance(spec, str):
                path = spec
                scale = 1.0
                offset = 0.0
            else:
                path = spec.get("path")
                scale = float(spec.get("scale", 1.0))
                offset = float(spec.get("offset", 0.0))
            values = extract_path(payload, path)
            data[name] = normalize_field(values, scale, offset)

        df = pd.DataFrame(data)
        if len(df) == 1 and len(times) > 1:
            df = pd.concat([df] * len(times), ignore_index=True)
        if len(times) == 1 and len(df) > 1:
            times = pd.to_datetime([times[0]] * len(df))

        df.index = pd.DatetimeIndex(times)
        df.index.name = "time"

        timezone = self.config.get("timezone")
        if timezone:
            if df.index.tz is None:
                df.index = df.index.tz_localize(timezone)
            else:
                df.index = df.index.tz_convert(timezone)
        return df


def build_weather_request_window(
    weather_config: Union[str, Path],
    departure: datetime,
    mission_end: datetime,
) -> Dict[str, Any]:
    """为整段任务时间窗构建天气接口参数。"""

    cfg = load_config(weather_config)
    base_url = str(cfg.get("base_url", "")).lower()
    if "open-meteo.com" not in base_url:
        return {}

    now_local = datetime.now(departure.tzinfo) if departure.tzinfo else datetime.now()
    horizon_h = max(2, int(np.ceil((mission_end - now_local).total_seconds() / 3600.0)) + 2)
    horizon_h = min(horizon_h, 16 * 24)
    return {
        "forecast_days": None,
        "forecast_hours": str(horizon_h),
    }


def fetch_open_meteo_aqi(
    point: GeoPoint,
    timezone: str,
    forecast_hours: Optional[int] = None,
) -> pd.DataFrame:
    """从 Open-Meteo 空气质量接口拉取 AQI。"""

    params = {
        "latitude": point.lat,
        "longitude": point.lon,
        "hourly": "us_aqi",
        "timezone": timezone,
    }
    if forecast_hours is not None and forecast_hours > 0:
        params["forecast_hours"] = int(forecast_hours)

    response = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    times = payload.get("hourly", {}).get("time", [])
    aqi = payload.get("hourly", {}).get("us_aqi", [])
    if not times or not aqi:
        return pd.DataFrame(columns=["air_quality_index"])

    df = pd.DataFrame(
        {"air_quality_index": pd.to_numeric(pd.Series(aqi), errors="coerce")},
        index=pd.to_datetime(times, errors="coerce"),
    )
    df.index.name = "time"
    if timezone:
        if df.index.tz is None:
            df.index = df.index.tz_localize(timezone)
        else:
            df.index = df.index.tz_convert(timezone)
    return df.dropna(how="all")


def align_timezones(
    df: pd.DataFrame,
    target_times: pd.DatetimeIndex,
) -> Tuple[pd.DataFrame, pd.DatetimeIndex]:
    """对齐天气数据与目标时间索引的时区。"""

    df_idx = df.index
    if df_idx.tz is None and target_times.tz is None:
        return df, target_times
    if df_idx.tz is None and target_times.tz is not None:
        return df.tz_localize(target_times.tz), target_times
    if df_idx.tz is not None and target_times.tz is None:
        return df, target_times.tz_localize(df_idx.tz)
    if str(df_idx.tz) != str(target_times.tz):
        return df, target_times.tz_convert(df_idx.tz)
    return df, target_times


def interpolate_weather(df: pd.DataFrame, target_times: pd.DatetimeIndex) -> pd.DataFrame:
    """按时间插值天气序列。"""

    df = df.copy()
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()
    df, target_times = align_timezones(df, target_times)
    merged = df.reindex(df.index.union(target_times)).sort_index()
    merged = merged.interpolate(method="time").ffill().bfill()
    return merged.loc[target_times]


def build_route_points(start: GeoPoint, end: GeoPoint, steps: int) -> List[GeoPoint]:
    """按起点终点线性插值生成抽象航线点。"""

    if steps < 2:
        return [start, end]
    points = []
    for idx in range(steps):
        ratio = idx / (steps - 1)
        points.append(
            GeoPoint(
                lat=start.lat + (end.lat - start.lat) * ratio,
                lon=start.lon + (end.lon - start.lon) * ratio,
                alt_m=start.alt_m + (end.alt_m - start.alt_m) * ratio,
            )
        )
    return points


def row_value(row: pd.Series, keys: List[str], default: float = np.nan) -> float:
    """从多候选字段中取第一个有效数值。"""

    for key in keys:
        if key in row.index:
            value = pd.to_numeric(pd.Series([row[key]]), errors="coerce").iloc[0]
            if np.isfinite(value):
                return float(value)
    return float(default)


def interp_optional(
    row0: pd.Series,
    row1: pd.Series,
    frac: float,
    keys: List[str],
    default: float = np.nan,
) -> float:
    """插值读取可选天气字段。"""

    v0 = row_value(row0, keys, np.nan)
    v1 = row_value(row1, keys, np.nan)
    if np.isfinite(v0) and np.isfinite(v1):
        return float(v0 * (1.0 - frac) + v1 * frac)
    if np.isfinite(v0):
        return float(v0)
    if np.isfinite(v1):
        return float(v1)
    return float(default)


def circular_interp_deg(angle0: float, angle1: float, frac: float) -> float:
    """按圆周角度插值，避免 359 度到 1 度被当成大跨度变化。"""

    if not np.isfinite(angle0) and not np.isfinite(angle1):
        return float("nan")
    if np.isfinite(angle0) and not np.isfinite(angle1):
        return float(angle0)
    if np.isfinite(angle1) and not np.isfinite(angle0):
        return float(angle1)
    rad0 = np.deg2rad(angle0)
    rad1 = np.deg2rad(angle1)
    x = np.cos(rad0) * (1.0 - frac) + np.cos(rad1) * frac
    y = np.sin(rad0) * (1.0 - frac) + np.sin(rad1) * frac
    return float((np.rad2deg(np.arctan2(y, x)) + 360.0) % 360.0)


def height_aware_wind(row: pd.Series, altitude_m: float) -> Tuple[float, float]:
    """按飞行高度在 10m 与 100m 风场之间做线性插值。"""

    wind10 = row_value(row, ["wind_speed_mps", "wind_speed_10m_mps"], np.nan)
    dir10 = row_value(row, ["wind_dir_deg", "wind_dir_10m_deg"], np.nan)
    wind100 = row_value(row, ["wind_speed_100m_mps"], np.nan)
    dir100 = row_value(row, ["wind_dir_100m_deg"], np.nan)
    if not np.isfinite(wind100) or not np.isfinite(dir100):
        return float(wind10), float(dir10)
    if not np.isfinite(wind10) or not np.isfinite(dir10):
        return float(wind100), float(dir100)

    frac = float(np.clip((float(altitude_m) - 10.0) / 90.0, 0.0, 1.0))
    wind_speed = wind10 * (1.0 - frac) + wind100 * frac
    wind_dir = circular_interp_deg(dir10, dir100, frac)
    return float(wind_speed), float(wind_dir)


def estimate_visibility_km(rh: float, precip_mm: float, wind_mps: float) -> float:
    """估算能见度。"""

    rh_v = float(rh) if np.isfinite(rh) else 65.0
    precip_v = float(precip_mm) if np.isfinite(precip_mm) else 0.0
    wind_v = float(wind_mps) if np.isfinite(wind_mps) else 3.0
    visibility = 24.0 - 0.11 * rh_v - 5.0 * max(precip_v, 0.0) + 0.55 * min(max(wind_v, 0.0), 12.0)
    return float(np.clip(visibility, 1.0, 25.0))


def estimate_aqi(
    visibility_km: float,
    rh: float,
    wind_mps: float,
    precip_mm: float,
    pressure_hpa: float,
) -> float:
    """估算空气质量指数。"""

    score = 45.0
    if np.isfinite(visibility_km):
        score += max(0.0, 10.0 - visibility_km) * 5.2
    if np.isfinite(rh):
        score += max(0.0, rh - 65.0) * 0.55
    if np.isfinite(wind_mps):
        score += max(0.0, 2.5 - wind_mps) * 7.5
        score -= max(0.0, wind_mps - 6.0) * 1.9
    if np.isfinite(precip_mm):
        score -= min(max(precip_mm, 0.0), 2.0) * 5.0
    if np.isfinite(pressure_hpa):
        score += max(0.0, pressure_hpa - 1020.0) * 0.16
    return float(np.clip(score, 10.0, 300.0))


def build_flight_time_index(
    frame: pd.DataFrame,
    timezone: str,
    date_col: str = "date",
    local_time_col: str = "local_time",
    elapsed_col: str = "time",
) -> pd.DatetimeIndex:
    """根据飞行日期、本地起飞时间和相对秒数构建绝对时间索引。"""

    if frame.empty:
        return pd.DatetimeIndex([])
    if date_col not in frame.columns or local_time_col not in frame.columns or elapsed_col not in frame.columns:
        raise WeatherConfigError("历史天气回填缺少 date/local_time/time 字段。")

    date_value = str(frame[date_col].iloc[0]).strip()
    local_time_value = str(frame[local_time_col].iloc[0]).strip()
    if not date_value or not local_time_value:
        raise WeatherConfigError("历史天气回填无法解析起飞本地时间。")

    start_local = pd.to_datetime("{} {}".format(date_value, local_time_value), errors="coerce")
    if pd.isna(start_local):
        raise WeatherConfigError("无法解析飞行起始时间: {} {}".format(date_value, local_time_value))

    elapsed_seconds = pd.to_numeric(frame[elapsed_col], errors="coerce").fillna(0.0)
    time_index = pd.DatetimeIndex(start_local + pd.to_timedelta(elapsed_seconds, unit="s"))
    if timezone:
        time_index = time_index.tz_localize(timezone)
    return time_index


def join_historical_weather(
    input_csv: Union[str, Path],
    output_csv: Union[str, Path],
    weather_config: Union[str, Path],
    route: Optional[str] = None,
    timezone: str = "America/New_York",
    cache_precision: int = 2,
) -> pd.DataFrame:
    """将历史天气按飞行时刻回填到飞行日志。"""

    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError("输入飞行日志不存在: {}".format(input_path))

    frame = pd.read_csv(input_path, low_memory=False)
    if route and "route" in frame.columns:
        frame = frame[frame["route"] == route].copy()
    if frame.empty:
        raise ValueError("历史天气回填后无可处理数据。")

    required_columns = {"flight", "time", "date", "local_time", "position_x", "position_y"}
    missing_columns = sorted(required_columns.difference(frame.columns))
    if missing_columns:
        raise ValueError("历史天气回填缺少必要列: {}".format(", ".join(missing_columns)))

    client = GenericWeatherClient(weather_config)
    enriched_parts: List[pd.DataFrame] = []
    weather_cache: Dict[Tuple[float, float, str, str, str], pd.DataFrame] = {}

    for _, group in frame.groupby("flight", sort=False):
        group = group.sort_values("time").reset_index(drop=True)
        time_index = build_flight_time_index(group, timezone=timezone)
        start_date = time_index.min().date().isoformat()
        end_date = time_index.max().date().isoformat()

        lat_value = float(pd.to_numeric(group["position_y"], errors="coerce").mean())
        lon_value = float(pd.to_numeric(group["position_x"], errors="coerce").mean())
        cache_key = (
            round(lat_value, cache_precision),
            round(lon_value, cache_precision),
            start_date,
            end_date,
            timezone,
        )

        if cache_key not in weather_cache:
            weather_cache[cache_key] = client.fetch_hourly(
                GeoPoint(lat=lat_value, lon=lon_value),
                extra_params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "timezone": timezone,
                },
            )

        interpolated = interpolate_weather(weather_cache[cache_key], time_index).reset_index(drop=True)
        merged = group.reset_index(drop=True).copy()
        for column in interpolated.columns:
            prefixed_column = "hist_{}".format(column)
            merged[prefixed_column] = interpolated[column].to_numpy()

        fill_columns = [
            "temperature_c",
            "relative_humidity_pct",
            "pressure_hpa",
            "precipitation_mm",
            "wind_gust_mps",
        ]
        for column in fill_columns:
            hist_column = "hist_{}".format(column)
            if hist_column not in merged.columns:
                continue
            if column not in merged.columns:
                merged[column] = merged[hist_column]
            else:
                merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(
                    pd.to_numeric(merged[hist_column], errors="coerce")
                )

        enriched_parts.append(merged)

    out = pd.concat(enriched_parts, ignore_index=True)
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out
