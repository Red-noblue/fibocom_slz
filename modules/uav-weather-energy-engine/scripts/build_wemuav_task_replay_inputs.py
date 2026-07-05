# 将 WEMUAV 分段训练表转换为任务级推理输入，服务风场/阶段补强回放评估。
"""构建 WEMUAV 任务回放输入。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pandas as pd


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="把 WEMUAV 训练表转换为任务级回放输入。")
    parser.add_argument(
        "--input",
        default="outputs/multi_source_training/wemuav_power_preflight.csv",
        help="WEMUAV 飞前训练表",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/wemuav_task_replay_inputs",
        help="任务回放输入输出目录",
    )
    parser.add_argument(
        "--task-mode",
        default="polyline",
        choices=["endpoint_only", "polyline", "both"],
        help="生成仅起终点任务、折线任务，或两者都生成",
    )
    return parser.parse_args()


def _fallback_float(row: pd.Series, *columns: str, default: float = 0.0) -> float:
    """按候选列顺序读取首个有效数值，避免历史列为空时整列塌掉。"""

    for column in columns:
        if column in row.index:
            value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
            if pd.notna(value):
                return float(value)
    return float(default)


def main() -> None:
    """执行转换。"""

    args = parse_args()
    input_path = _resolve_path(args.input)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = output_dir / "tasks"
    weather_dir = output_dir / "weather"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    weather_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    rows = []
    for flight_id, group in df.groupby("flight", sort=True):
        ordered = group.sort_values(["segment_start_s", "segment_id"], na_position="last").copy()
        first = ordered.iloc[0]
        last = ordered.iloc[-1]
        departure_time = None
        for column in ["start_time", "mid_time", "end_time"]:
            if column in ordered.columns:
                parsed = pd.to_datetime(first[column], errors="coerce")
                if pd.notna(parsed):
                    departure_time = parsed.isoformat()
                    break
        if departure_time is None:
            date_value = pd.to_datetime(first.get("date"), errors="coerce")
            departure_time = date_value.isoformat() if pd.notna(date_value) else "2026-01-01T00:00:00"

        base_task_payload = {
            "route_name": str(first.get("route", f"flight_{flight_id}")),
            "departure_time": departure_time,
            "start": {
                "lat": float(first["start_lat"]),
                "lon": float(first["start_lon"]),
                "alt_m": float(first.get("altitude_start_m", first.get("altitude_m", 0.0))),
            },
            "end": {
                "lat": float(last["end_lat"]),
                "lon": float(last["end_lon"]),
                "alt_m": float(last.get("altitude_end_m", last.get("altitude_m", 0.0))),
            },
            "vehicle": {
                "name": "WEMUAV_Phantom4Pro",
                "payload_g": float(first.get("payload_g", 0.0)),
                "cruise_speed_mps": float(ordered["speed_mps"].median()),
                "altitude_m": float(ordered["altitude_m"].median()),
            },
            "battery": {
                "capacity_wh": 130.0,
                "nominal_voltage_v": 15.2,
            },
            "mission": {
                "step_minutes": max(
                    1,
                    int(round(float(pd.to_numeric(ordered["duration_s"], errors="coerce").median()) / 60.0)),
                ),
            },
        }
        route_points = [
            {
                "lat": float(first["start_lat"]),
                "lon": float(first["start_lon"]),
                "alt_m": float(first.get("altitude_start_m", first.get("altitude_m", 0.0))),
            }
        ]
        route_segments = []
        for _, seg in ordered.iterrows():
            route_segments.append(
                {
                    "segment_id": int(seg.get("segment_id", len(route_segments))),
                    "start": {
                        "lat": float(seg["start_lat"]),
                        "lon": float(seg["start_lon"]),
                        "alt_m": float(seg.get("altitude_start_m", seg.get("altitude_m", 0.0))),
                    },
                    "end": {
                        "lat": float(seg["end_lat"]),
                        "lon": float(seg["end_lon"]),
                        "alt_m": float(seg.get("altitude_end_m", seg.get("altitude_m", 0.0))),
                    },
                    "distance_m": float(seg["distance_m"]),
                    "duration_s": float(seg["duration_s"]),
                }
            )
            route_points.append(
                {
                    "lat": float(seg["end_lat"]),
                    "lon": float(seg["end_lon"]),
                    "alt_m": float(seg.get("altitude_end_m", seg.get("altitude_m", 0.0))),
                }
            )
        weather_rows = []
        for _, row in ordered.iterrows():
            timestamp = None
            for column in ["mid_time", "start_time", "end_time"]:
                if column in ordered.columns:
                    parsed = pd.to_datetime(row[column], errors="coerce")
                    if pd.notna(parsed):
                        timestamp = parsed.isoformat()
                        break
            if timestamp is None:
                base_time = pd.to_datetime(first.get("date"), errors="coerce")
                if pd.isna(base_time):
                    continue
                timestamp = (base_time + pd.to_timedelta(float(row.get("segment_start_s", 0.0)), unit="s")).isoformat()
            weather_rows.append(
                {
                    "time": timestamp,
                    "wind_speed_mps": _fallback_float(row, "hist_wind_speed_mps", "wind_speed_mps"),
                    "wind_dir_deg": _fallback_float(row, "hist_wind_dir_deg", "wind_dir_deg"),
                    "wind_speed_100m_mps": _fallback_float(
                        row,
                        "hist_wind_speed_100m_mps",
                        "wind_speed_100m_mps",
                        "hist_wind_speed_mps",
                        "wind_speed_mps",
                    ),
                    "wind_dir_100m_deg": _fallback_float(
                        row,
                        "hist_wind_dir_100m_deg",
                        "wind_dir_100m_deg",
                        "hist_wind_dir_deg",
                        "wind_dir_deg",
                    ),
                    "wind_gust_mps": _fallback_float(row, "hist_wind_gust_mps", "wind_gust_mps"),
                    "temperature_c": _fallback_float(row, "hist_temperature_c", "temperature_c"),
                    "relative_humidity_pct": _fallback_float(row, "hist_relative_humidity_pct", "relative_humidity_pct"),
                    "pressure_hpa": _fallback_float(row, "hist_pressure_hpa", "pressure_hpa", default=1013.25),
                    "precipitation_mm": _fallback_float(row, "hist_precipitation_mm", "precipitation_mm"),
                    "air_density_kgm3": _fallback_float(row, "hist_air_density_kgm3", "air_density_kgm3", default=1.225),
                }
            )
        weather_path = weather_dir / f"flight_{int(flight_id)}.csv"
        pd.DataFrame(weather_rows).to_csv(weather_path, index=False)

        task_variants = []
        if args.task_mode in {"endpoint_only", "both"}:
            task_variants.append(("endpoint_only", dict(base_task_payload)))
        if args.task_mode in {"polyline", "both"}:
            polyline_payload = dict(base_task_payload)
            polyline_payload["route_points"] = route_points
            polyline_payload["route_segments"] = route_segments
            task_variants.append(("polyline", polyline_payload))

        for task_mode, task_payload in task_variants:
            task_path = tasks_dir / f"flight_{int(flight_id)}__{task_mode}.json"
            task_path.write_text(json.dumps(task_payload, indent=2, ensure_ascii=False), encoding="utf-8")
            rows.append(
                {
                    "flight": int(flight_id),
                    "task_mode": task_mode,
                    "route": str(first.get("route", "")),
                    "task_config": str(task_path.resolve()),
                    "weather_frame": str(weather_path.resolve()),
                    "actual_total_energy_wh": float(pd.to_numeric(ordered["segment_energy_wh"], errors="coerce").sum()),
                    "actual_total_distance_m": float(pd.to_numeric(ordered["distance_m"], errors="coerce").sum()),
                    "payload_g": float(first.get("payload_g", 0.0)),
                    "cruise_speed_mps": float(ordered["speed_mps"].median()),
                    "altitude_m": float(ordered["altitude_m"].median()),
                    "segment_count": int(len(ordered.index)),
                }
            )
    manifest = pd.DataFrame(rows).sort_values(["flight", "task_mode"])
    manifest.to_csv(output_dir / "manifest.csv", index=False)
    print(json.dumps({"rows": int(len(manifest.index)), "manifest": str((output_dir / "manifest.csv").resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
