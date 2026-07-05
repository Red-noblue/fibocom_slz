from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import joblib
import numpy as np
import pandas as pd
import requests

from .common import bearing_deg, circular_mean_deg, ensure_dir, haversine_m
from .weather_client import GenericWeatherClient


@dataclass
class PredictionResult:
    summary: dict[str, Any]
    timeseries: pd.DataFrame


def parse_departure(value: str) -> datetime:
    if value.lower() == "now":
        return datetime.now()
    return pd.to_datetime(value).to_pydatetime()


def load_defaults(features_path: str | Path) -> dict[str, float]:
    df = pd.read_csv(features_path)
    return {
        "speed_mps": float(df["speed_mps"].median()),
        "payload_g": float(df["payload_g"].median()),
        "altitude_m": float(df["altitude_m"].median()),
    }


def detect_weather_source(config_path: str | Path) -> str:
    try:
        with Path(config_path).open("r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception:
        return "Unknown weather source"

    base_url = str(cfg.get("base_url", ""))
    base_url_lower = base_url.lower()
    if "open-meteo.com" in base_url_lower:
        return "Open-Meteo"
    if "cma" in base_url_lower:
        return "CMA"
    host = urlparse(base_url).netloc or base_url
    return f"Config-driven ({host})"


def build_weather_request_window(
    config_path: str | Path,
    departure: datetime,
    mission_end: datetime,
) -> dict[str, Any]:
    try:
        with Path(config_path).open("r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception:
        return {}

    base_url = str(cfg.get("base_url", "")).lower()
    if "open-meteo.com" not in base_url:
        return {}

    now_local = datetime.now(departure.tzinfo) if departure.tzinfo else datetime.now()
    horizon_h = max(2, int(math.ceil((mission_end - now_local).total_seconds() / 3600.0)) + 2)
    horizon_h = min(horizon_h, 16 * 24)
    return {
        "forecast_days": None,
        "forecast_hours": str(horizon_h),
    }


def fetch_open_meteo_aqi(
    latitude: float,
    longitude: float,
    timezone: str,
    forecast_hours: int | None = None,
) -> pd.DataFrame:
    params = {
        "latitude": latitude,
        "longitude": longitude,
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


def _row_value(row: pd.Series, keys: list[str], default: float = np.nan) -> float:
    for key in keys:
        if key in row.index:
            value = pd.to_numeric(pd.Series([row[key]]), errors="coerce").iloc[0]
            if np.isfinite(value):
                return float(value)
    return float(default)


def _interp_optional(
    row0: pd.Series,
    row1: pd.Series,
    frac: float,
    keys: list[str],
    default: float = np.nan,
) -> float:
    v0 = _row_value(row0, keys, np.nan)
    v1 = _row_value(row1, keys, np.nan)
    if np.isfinite(v0) and np.isfinite(v1):
        return float(v0 * (1.0 - frac) + v1 * frac)
    if np.isfinite(v0):
        return float(v0)
    if np.isfinite(v1):
        return float(v1)
    return float(default)


def estimate_visibility_km(rh: float, precip_mm: float, wind_mps: float) -> float:
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


def build_route_points(
    start: tuple[float, float],
    end: tuple[float, float],
    steps: int,
) -> list[tuple[float, float]]:
    if steps < 2:
        return [start, end]
    lat1, lon1 = start
    lat2, lon2 = end
    points = []
    for idx in range(steps):
        ratio = idx / (steps - 1)
        points.append(
            (
                lat1 + (lat2 - lat1) * ratio,
                lon1 + (lon2 - lon1) * ratio,
            )
        )
    return points


def _align_timezones(
    df: pd.DataFrame,
    target_times: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    df_idx = df.index
    if df_idx.tz is None and target_times.tz is None:
        return df, target_times
    if df_idx.tz is None and target_times.tz is not None:
        df = df.tz_localize(target_times.tz)
        return df, target_times
    if df_idx.tz is not None and target_times.tz is None:
        return df, target_times.tz_localize(df_idx.tz)
    if str(df_idx.tz) != str(target_times.tz):
        return df, target_times.tz_convert(df_idx.tz)
    return df, target_times


def interpolate_weather(df: pd.DataFrame, target_times: pd.DatetimeIndex) -> pd.DataFrame:
    df = df.copy()
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()
    df, target_times = _align_timezones(df, target_times)
    merged = df.reindex(df.index.union(target_times)).sort_index()
    merged = merged.interpolate(method="time").ffill().bfill()
    return merged.loc[target_times]


def wind_dir_interp(d1: float, d2: float, w1: float, w2: float) -> float:
    return circular_mean_deg([d1, d2], weights=[w1, w2])


def build_risk_alerts(summary: dict[str, Any]) -> list[str]:
    alerts = []
    total_energy = float(summary["predicted_total_energy_wh"])
    battery = float(summary["battery_wh"])
    route_len = float(summary["route_length_km"])
    predicted_range = float(summary["predicted_range_km"])

    if total_energy > battery:
        alerts.append("预测总能耗高于电池容量，实际飞行可能中途电量不足。")
    if predicted_range < route_len:
        alerts.append("按当前效率预测的续航里程不足以覆盖全程航线。")
    if not alerts:
        alerts.append("当前预测未触发硬性电量风险，但仍需结合实测风场复核。")
    return alerts


def predict_route_energy(
    model_path: str | Path,
    features_path: str | Path,
    route_name: str,
    start: tuple[float, float],
    end: tuple[float, float],
    speed_mps: float | None,
    payload_g: float | None,
    altitude_m: float | None,
    battery_wh: float,
    departure: datetime,
    step_minutes: int,
    weather_config: str | Path,
) -> PredictionResult:
    defaults = load_defaults(features_path)
    speed = speed_mps if speed_mps is not None else defaults["speed_mps"]
    payload = payload_g if payload_g is not None else defaults["payload_g"]
    altitude = altitude_m if altitude_m is not None else defaults["altitude_m"]

    total_distance_m = float(haversine_m(start[0], start[1], end[0], end[1]))
    total_distance_km = total_distance_m / 1000.0
    heading_deg = float(bearing_deg(start[0], start[1], end[0], end[1]))

    total_time_s = total_distance_m / speed
    step_seconds = max(60, int(step_minutes) * 60)
    steps = max(2, int(math.ceil(total_time_s / step_seconds)) + 1)
    times = [departure + timedelta(seconds=step_seconds * idx) for idx in range(steps)]
    time_index = pd.DatetimeIndex(times)

    mission_end = departure + timedelta(seconds=total_time_s)
    weather_window_params = build_weather_request_window(weather_config, departure, mission_end)

    client = GenericWeatherClient(weather_config)
    start_df = client.fetch_hourly(start[0], start[1], extra_params=weather_window_params)
    end_df = client.fetch_hourly(end[0], end[1], extra_params=weather_window_params)

    start_interp = interpolate_weather(start_df, time_index)
    end_interp = interpolate_weather(end_df, time_index)

    try:
        with Path(weather_config).open("r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        base_url = str(cfg.get("base_url", "")).lower()
        tz_name = str(cfg.get("timezone") or cfg.get("params", {}).get("timezone") or "Asia/Shanghai")
    except Exception:
        base_url = ""
        tz_name = "Asia/Shanghai"

    if "open-meteo.com" in base_url:
        try:
            forecast_hours = pd.to_numeric(
                pd.Series([weather_window_params.get("forecast_hours")]),
                errors="coerce",
            ).iloc[0]
            forecast_hours = int(forecast_hours) if np.isfinite(forecast_hours) else None
            aqi_start_df = fetch_open_meteo_aqi(start[0], start[1], tz_name, forecast_hours=forecast_hours)
            aqi_end_df = fetch_open_meteo_aqi(end[0], end[1], tz_name, forecast_hours=forecast_hours)
            if not aqi_start_df.empty:
                start_interp["air_quality_index"] = interpolate_weather(
                    aqi_start_df,
                    time_index,
                )["air_quality_index"].to_numpy()
            if not aqi_end_df.empty:
                end_interp["air_quality_index"] = interpolate_weather(
                    aqi_end_df,
                    time_index,
                )["air_quality_index"].to_numpy()
        except Exception:
            pass

    model = joblib.load(model_path)
    base_cols = model["base_cols"]
    feature_cols = model["feature_cols"]

    distances = np.linspace(0.0, total_distance_m, steps)
    points = build_route_points(start, end, steps)

    rows = []
    cumulative_energy = 0.0
    reachable_distance_m = total_distance_m
    reachable_time_s = total_time_s
    depleted = False

    first_weather = start_interp.iloc[0]
    first_wind = float(first_weather["wind_speed_mps"])
    first_temp = float(first_weather["temperature_c"])
    first_rh = float(first_weather["relative_humidity_pct"])
    first_pressure = float(first_weather["pressure_hpa"])
    first_precip = float(first_weather["precipitation_mm"])

    first_vis_km = _row_value(first_weather, ["visibility_km"], np.nan)
    if not np.isfinite(first_vis_km):
        vis_m = _row_value(first_weather, ["visibility_m", "visibility"], np.nan)
        first_vis_km = vis_m / 1000.0 if np.isfinite(vis_m) else np.nan
    if not np.isfinite(first_vis_km):
        first_vis_km = estimate_visibility_km(first_rh, first_precip, first_wind)

    first_uv = _row_value(first_weather, ["uv_index", "uv", "ultraviolet_index"], np.nan)
    if not np.isfinite(first_uv):
        first_uv = 2.0 if 9 <= time_index[0].hour <= 16 else 0.0

    first_aqi = _row_value(first_weather, ["air_quality_index", "us_aqi", "european_aqi", "aqi"], np.nan)
    if not np.isfinite(first_aqi):
        first_aqi = estimate_aqi(first_vis_km, first_rh, first_wind, first_precip, first_pressure)

    rows.append(
        {
            "time": time_index[0].isoformat(),
            "lat": points[0][0],
            "lon": points[0][1],
            "distance_from_start_km": 0.0,
            "segment_distance_km": 0.0,
            "wind_speed_mps": first_wind,
            "wind_dir_deg": float(first_weather["wind_dir_deg"]),
            "headwind_mps": 0.0,
            "crosswind_mps": 0.0,
            "temperature_c": first_temp,
            "relative_humidity_pct": first_rh,
            "pressure_hpa": first_pressure,
            "precipitation_mm": first_precip,
            "visibility_km": float(first_vis_km),
            "uv_index": float(first_uv),
            "air_quality_index": float(first_aqi),
            "weather_factor": 1.0,
            "energy_wh_per_km": 0.0,
            "segment_energy_wh": 0.0,
            "cumulative_energy_wh": 0.0,
            "remaining_battery_wh": float(battery_wh),
            "cruise_speed_mps": speed,
            "cruise_altitude_m": altitude,
            "payload_g": payload,
        }
    )

    for idx in range(steps - 1):
        frac = distances[idx] / total_distance_m if total_distance_m > 0 else 0.0
        weather_start = start_interp.iloc[idx]
        weather_end = end_interp.iloc[idx]

        wind_speed = float(weather_start["wind_speed_mps"] * (1.0 - frac) + weather_end["wind_speed_mps"] * frac)
        wind_dir = float(
            wind_dir_interp(
                float(weather_start["wind_dir_deg"]),
                float(weather_end["wind_dir_deg"]),
                1.0 - frac,
                frac,
            )
        )
        rel = np.deg2rad((wind_dir - heading_deg) % 360.0)
        headwind = wind_speed * np.cos(rel)
        crosswind = wind_speed * np.sin(rel)

        temp_c = float(weather_start["temperature_c"] * (1.0 - frac) + weather_end["temperature_c"] * frac)
        rh = float(
            weather_start["relative_humidity_pct"] * (1.0 - frac)
            + weather_end["relative_humidity_pct"] * frac
        )
        pressure = float(weather_start["pressure_hpa"] * (1.0 - frac) + weather_end["pressure_hpa"] * frac)
        precip = float(weather_start["precipitation_mm"] * (1.0 - frac) + weather_end["precipitation_mm"] * frac)

        visibility_km = _interp_optional(weather_start, weather_end, frac, ["visibility_km"], default=np.nan)
        if not np.isfinite(visibility_km):
            visibility_m = _interp_optional(
                weather_start,
                weather_end,
                frac,
                ["visibility_m", "visibility"],
                default=np.nan,
            )
            if np.isfinite(visibility_m):
                visibility_km = visibility_m / 1000.0
        if not np.isfinite(visibility_km):
            visibility_km = estimate_visibility_km(rh, precip, wind_speed)
        visibility_km = float(np.clip(visibility_km, 0.2, 30.0))

        uv_index = _interp_optional(
            weather_start,
            weather_end,
            frac,
            ["uv_index", "uv", "ultraviolet_index"],
            default=np.nan,
        )
        if not np.isfinite(uv_index):
            uv_index = 2.0 if 9 <= time_index[idx + 1].hour <= 16 else 0.0
        uv_index = float(np.clip(uv_index, 0.0, 16.0))

        air_quality_index = _interp_optional(
            weather_start,
            weather_end,
            frac,
            ["air_quality_index", "us_aqi", "european_aqi", "aqi"],
            default=np.nan,
        )
        if not np.isfinite(air_quality_index):
            air_quality_index = estimate_aqi(visibility_km, rh, wind_speed, precip, pressure)
        air_quality_index = float(np.clip(air_quality_index, 0.0, 500.0))

        features = pd.DataFrame(
            [
                {
                    "speed_mps": speed,
                    "payload_kg": payload / 1000.0,
                    "altitude_m": altitude,
                    "wind_speed_mps": wind_speed,
                    "headwind_mps": headwind,
                    "crosswind_mps": crosswind,
                }
            ]
        )
        baseline = float(model["baseline"].predict(features[base_cols])[0])
        residual = float(model["residual"].predict(features[feature_cols])[0])
        energy_per_km = baseline + residual

        weather_factor = 1.0
        weather_factor += 0.006 * max(0.0, abs(temp_c - 22.0) - 4.0)
        weather_factor += 0.030 * min(max(precip, 0.0), 3.0)
        weather_factor += 0.0015 * max(0.0, rh - 70.0)
        weather_factor += 0.0012 * max(0.0, 1013.25 - pressure)
        weather_factor += 0.0025 * max(0.0, 8.0 - visibility_km)
        weather_factor += 0.0010 * max(0.0, uv_index - 6.0)
        weather_factor += 0.0008 * max(0.0, air_quality_index - 80.0)
        weather_factor = float(np.clip(weather_factor, 0.85, 1.75))

        seg_dist_m = float(distances[idx + 1] - distances[idx])
        seg_energy = float(energy_per_km * weather_factor * (seg_dist_m / 1000.0))
        cumulative_energy += seg_energy

        if (not depleted) and cumulative_energy >= battery_wh:
            depleted = True
            excess = cumulative_energy - battery_wh
            frac_seg = max(0.0, 1.0 - excess / seg_energy) if seg_energy > 0 else 0.0
            reachable_distance_m = float(distances[idx] + seg_dist_m * frac_seg)
            reachable_time_s = float(idx * step_seconds + step_seconds * frac_seg)

        rows.append(
            {
                "time": time_index[idx + 1].isoformat(),
                "lat": points[idx + 1][0],
                "lon": points[idx + 1][1],
                "distance_from_start_km": float(distances[idx + 1] / 1000.0),
                "segment_distance_km": float(seg_dist_m / 1000.0),
                "wind_speed_mps": wind_speed,
                "wind_dir_deg": wind_dir,
                "headwind_mps": headwind,
                "crosswind_mps": crosswind,
                "temperature_c": temp_c,
                "relative_humidity_pct": rh,
                "pressure_hpa": pressure,
                "precipitation_mm": precip,
                "visibility_km": visibility_km,
                "uv_index": uv_index,
                "air_quality_index": air_quality_index,
                "weather_factor": weather_factor,
                "energy_wh_per_km": float(energy_per_km),
                "segment_energy_wh": seg_energy,
                "cumulative_energy_wh": float(cumulative_energy),
                "remaining_battery_wh": max(0.0, float(battery_wh - cumulative_energy)),
                "cruise_speed_mps": speed,
                "cruise_altitude_m": altitude,
                "payload_g": payload,
            }
        )

    timeseries = pd.DataFrame(rows)
    if battery_wh > 0:
        timeseries["battery_remaining_pct"] = np.clip(
            timeseries["remaining_battery_wh"] / battery_wh * 100.0,
            0.0,
            100.0,
        )
    else:
        timeseries["battery_remaining_pct"] = 0.0

    summary = {
        "route_name": route_name,
        "route_start": {"lat": start[0], "lon": start[1]},
        "route_end": {"lat": end[0], "lon": end[1]},
        "route_heading_deg": heading_deg,
        "route_length_km": total_distance_km,
        "cruise_speed_mps": speed,
        "cruise_altitude_m": altitude,
        "payload_g": payload,
        "battery_wh": battery_wh,
        "departure_time": departure.isoformat(),
        "planned_flight_time_s": total_time_s,
        "predicted_total_energy_wh": float(timeseries["segment_energy_wh"].sum()),
        "predicted_range_km": reachable_distance_m / 1000.0,
        "predicted_flight_time_s": reachable_time_s,
        "weather_source": detect_weather_source(weather_config),
    }
    summary["risk_alerts"] = build_risk_alerts(summary)
    return PredictionResult(summary=summary, timeseries=timeseries)


def write_prediction_outputs(result: PredictionResult, output_dir: str | Path) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    ensure_dir(output_path)

    summary_path = output_path / "realtime_route_summary.json"
    timeseries_path = output_path / "realtime_route_timeseries.csv"

    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(result.summary, fh, indent=2, ensure_ascii=False)
    result.timeseries.to_csv(timeseries_path, index=False)
    return summary_path, timeseries_path
