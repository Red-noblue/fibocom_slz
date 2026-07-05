"""第一阶段简化无人机任务仿真器。"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any


EARTH_RADIUS_M = 6371000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2.0) ** 2
    return EARTH_RADIUS_M * 2.0 * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    dlon = lon2_r - lon1_r
    y = math.sin(dlon) * math.cos(lat2_r)
    x = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def interpolate(start: float, end: float, fraction: float) -> float:
    return start + (end - start) * fraction


def wind_components(wind_speed_mps: float, wind_dir_deg: float, heading_deg: float) -> tuple[float, float]:
    rel = math.radians((wind_dir_deg - heading_deg) % 360.0)
    headwind = wind_speed_mps * math.cos(rel)
    crosswind = abs(wind_speed_mps * math.sin(rel))
    return headwind, crosswind


def _risk_add(environment: dict[str, Any], fraction: float) -> float:
    score = 0.0
    for zone in environment.get("risk_zones", []):
        if float(zone.get("start_fraction", 0.0)) <= fraction <= float(zone.get("end_fraction", 0.0)):
            score += float(zone.get("risk_score_add", 0.0))
    return score


def simulate_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    start = scenario["start"]
    end = scenario["end"]
    vehicle = scenario["vehicle"]
    weather = scenario["weather"]
    environment = scenario["environment"]

    distance_m = haversine_m(start["lat"], start["lon"], end["lat"], end["lon"])
    heading = bearing_deg(start["lat"], start["lon"], end["lat"], end["lon"])
    speed_mps = float(scenario["cruise_speed_mps"])
    step_seconds = int(scenario.get("step_seconds", 30))
    duration_s = max(step_seconds, distance_m / max(speed_mps, 0.1))
    steps = max(2, math.ceil(duration_s / step_seconds) + 1)
    departure = datetime.fromisoformat(scenario["departure"])

    wind_speed = float(weather["wind_speed_mps"])
    wind_dir = float(weather["wind_dir_deg"])
    gust = float(weather.get("gust_mps", 0.0))
    temperature = float(weather["temperature_c"])
    pressure = float(weather["pressure_hpa"])
    humidity = float(weather["relative_humidity_pct"])
    precip = float(weather.get("precipitation_mm_h", 0.0))

    headwind, crosswind = wind_components(wind_speed, wind_dir, heading)
    base_power = float(vehicle["cruise_power_w"])
    headwind_power = max(0.0, headwind) * float(vehicle["headwind_power_w_per_mps"])
    crosswind_power = crosswind * float(vehicle["crosswind_power_w_per_mps"])
    low_temp_pct = max(0.0, 15.0 - temperature) * float(vehicle["low_temp_power_pct_per_c_below_15"])
    battery_wh = float(vehicle["battery_wh"])

    rows: list[dict[str, Any]] = []
    cumulative_wh = 0.0
    for idx in range(steps):
        fraction = min(1.0, idx / max(steps - 1, 1))
        if idx == 0:
            dt_s = 0.0
        else:
            dt_s = min(float(step_seconds), max(0.0, duration_s - step_seconds * (idx - 1)))
        gust_wave = gust * max(0.0, math.sin(math.pi * fraction)) * (0.5 + 0.5 * math.sin(8.0 * math.pi * fraction))
        dynamic_power = base_power + headwind_power + crosswind_power + max(0.0, gust_wave) * 14.0
        dynamic_power *= 1.0 + low_temp_pct
        if fraction < 0.08:
            dynamic_power += float(vehicle["climb_power_w_per_mps"]) * 1.2
        if fraction > 0.92:
            dynamic_power -= float(vehicle["descent_power_credit_w_per_mps"]) * 0.8
        dynamic_power = max(float(vehicle["hover_power_w"]) * 0.55, dynamic_power)
        cumulative_wh += dynamic_power * dt_s / 3600.0
        remaining_wh = max(0.0, battery_wh - cumulative_wh)
        risk_score = min(
            100.0,
            18.0
            + max(0.0, headwind) * 3.0
            + crosswind * 1.1
            + precip * 8.0
            + _risk_add(environment, fraction),
        )
        rows.append(
            {
                "time": (departure + timedelta(seconds=step_seconds * idx)).isoformat(),
                "lat": interpolate(float(start["lat"]), float(end["lat"]), fraction),
                "lon": interpolate(float(start["lon"]), float(end["lon"]), fraction),
                "altitude_m": float(scenario["cruise_altitude_m"]),
                "distance_from_start_km": distance_m * fraction / 1000.0,
                "speed_mps": speed_mps,
                "heading_deg": heading,
                "wind_speed_mps": wind_speed + gust_wave,
                "wind_dir_deg": wind_dir,
                "headwind_mps": headwind,
                "crosswind_mps": crosswind,
                "temperature_c": temperature,
                "pressure_hpa": pressure,
                "relative_humidity_pct": humidity,
                "power_w": dynamic_power,
                "cumulative_energy_wh": cumulative_wh,
                "remaining_battery_wh": remaining_wh,
                "battery_remaining_pct": remaining_wh / battery_wh * 100.0 if battery_wh > 0 else 0.0,
                "risk_score": risk_score,
            }
        )

    reserve_pct = float(vehicle.get("reserve_battery_pct", 20.0))
    final_pct = rows[-1]["battery_remaining_pct"]
    summary = {
        "scenario_name": scenario["name"],
        "route_name": scenario["route_name"],
        "route_start": start,
        "route_end": end,
        "route_length_km": distance_m / 1000.0,
        "planned_flight_time_s": duration_s,
        "cruise_altitude_m": float(scenario["cruise_altitude_m"]),
        "cruise_speed_mps": speed_mps,
        "route_heading_deg": heading,
        "battery_wh": battery_wh,
        "sim_total_energy_wh": cumulative_wh,
        "sim_remaining_battery_wh": rows[-1]["remaining_battery_wh"],
        "sim_remaining_battery_pct": final_pct,
        "max_risk_score": max(row["risk_score"] for row in rows),
        "risk_label": "insufficient_reserve" if final_pct < reserve_pct else "acceptable",
        "weather_name": weather.get("name"),
        "vehicle_name": vehicle.get("name"),
        "environment_name": environment.get("name"),
    }
    return {"summary": summary, "timeseries": rows}
