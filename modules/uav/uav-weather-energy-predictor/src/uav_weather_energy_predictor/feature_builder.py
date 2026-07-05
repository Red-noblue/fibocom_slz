from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .common import bearing_deg, circular_mean_deg, ensure_dir, haversine_m


def aggregate_flight(group: pd.DataFrame) -> dict:
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

    wind_speed = float(np.nanmean(group["wind_speed"].to_numpy(dtype=float)))
    wind_dir = circular_mean_deg(group["wind_angle"].to_numpy(dtype=float))

    headwind = float("nan")
    crosswind = float("nan")
    if not np.isnan(heading) and not np.isnan(wind_dir):
        rel = np.deg2rad((wind_dir - heading) % 360.0)
        headwind = wind_speed * np.cos(rel)
        crosswind = wind_speed * np.sin(rel)

    flight_time_s = float(time_s[-1] - time_s[0])
    return {
        "flight": int(group["flight"].iloc[0]),
        "route": str(group["route"].iloc[0]),
        "date": str(group["date"].iloc[0]),
        "speed_mps": float(np.nanmedian(group["speed"].to_numpy(dtype=float))),
        "payload_g": float(np.nanmedian(group["payload"].to_numpy(dtype=float))),
        "altitude_m": float(np.nanmedian(group["altitude"].to_numpy(dtype=float))),
        "wind_speed_mps": wind_speed,
        "wind_dir_deg": wind_dir,
        "headwind_mps": headwind,
        "crosswind_mps": crosswind,
        "heading_deg": heading,
        "distance_m": distance_m,
        "energy_wh": energy_wh,
        "flight_time_s": flight_time_s,
    }


def build_features(input_csv: str | Path, output_csv: str | Path, route: str | None = None) -> None:
    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"Input flights.csv not found: {input_path}")

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
        "date",
        "route",
    ]
    df = pd.read_csv(input_path, usecols=usecols, low_memory=False)

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
    ]
    for col in numeric_cols:
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
        raise ValueError("No usable flight rows were produced from the input dataset.")

    out["energy_wh_per_km"] = out["energy_wh"] / (out["distance_m"] / 1000.0)

    output_path = Path(output_csv)
    ensure_dir(output_path.parent)
    out.to_csv(output_path, index=False)

    route_summary = (
        out.groupby("route")
        .agg(
            route_length_m=("distance_m", "mean"),
            route_heading_deg=("heading_deg", lambda x: circular_mean_deg(x.to_numpy())),
            flight_count=("flight", "count"),
        )
        .reset_index()
    )
    route_summary["route_length_km"] = route_summary["route_length_m"] / 1000.0
    route_summary.to_csv(output_path.with_name("route_summary.csv"), index=False)
