# 分析任务级回放误差与路线过程特征的关系，定位高误差任务形态。
"""分析任务级回放误差。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd

from uav_energy_engine.evaluate import save_summary
from uav_energy_engine.utils import haversine_m, bearing_deg


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="分析任务级回放误差与路线过程特征。")
    parser.add_argument("--errors", required=True, help="task_replay_errors.csv")
    parser.add_argument("--manifest", required=True, help="manifest.csv")
    parser.add_argument("--output-dir", required=True, help="分析输出目录")
    return parser.parse_args()


def _load_task_features(task_path: Path) -> dict:
    """从任务配置解析路线过程特征。"""

    payload = json.loads(task_path.read_text(encoding="utf-8"))
    segments = payload.get("route_segments") or []
    if not segments:
        return {
            "task_has_segments": False,
            "route_direct_distance_m": float("nan"),
            "route_total_distance_m": float("nan"),
            "route_tortuosity": float("nan"),
            "route_segment_count": 0,
            "route_total_heading_change_deg": float("nan"),
            "route_total_altitude_gain_m": float("nan"),
            "route_total_altitude_loss_m": float("nan"),
            "route_altitude_range_m": float("nan"),
        }

    direct_distance_m = haversine_m(
        payload["start"]["lat"],
        payload["start"]["lon"],
        payload["end"]["lat"],
        payload["end"]["lon"],
    )
    total_distance_m = 0.0
    total_heading_change_deg = 0.0
    altitude_values = []
    heading_values = []
    total_gain = 0.0
    total_loss = 0.0
    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        total_distance_m += float(segment.get("distance_m") or haversine_m(start["lat"], start["lon"], end["lat"], end["lon"]))
        start_alt = float(start.get("alt_m", 0.0))
        end_alt = float(end.get("alt_m", 0.0))
        altitude_values.extend([start_alt, end_alt])
        delta = end_alt - start_alt
        total_gain += max(delta, 0.0)
        total_loss += max(-delta, 0.0)
        heading_values.append(bearing_deg(start["lat"], start["lon"], end["lat"], end["lon"]))

    for prev, curr in zip(heading_values[:-1], heading_values[1:]):
        delta = (curr - prev + 180.0) % 360.0 - 180.0
        total_heading_change_deg += abs(delta)

    altitude_range = max(altitude_values) - min(altitude_values) if altitude_values else float("nan")
    tortuosity = total_distance_m / direct_distance_m if direct_distance_m > 1e-9 else float("nan")
    return {
        "task_has_segments": True,
        "route_direct_distance_m": float(direct_distance_m),
        "route_total_distance_m": float(total_distance_m),
        "route_tortuosity": float(tortuosity),
        "route_segment_count": int(len(segments)),
        "route_total_heading_change_deg": float(total_heading_change_deg),
        "route_total_altitude_gain_m": float(total_gain),
        "route_total_altitude_loss_m": float(total_loss),
        "route_altitude_range_m": float(altitude_range),
    }


def _bin_series(frame: pd.DataFrame, column: str, labels: list[str]) -> pd.Series:
    """按分位数粗分箱，便于看误差切片。"""

    values = pd.to_numeric(frame[column], errors="coerce")
    valid = values.dropna()
    if valid.nunique() < 2:
        return pd.Series(["single_value"] * len(frame.index), index=frame.index, dtype=object)
    q = min(len(labels), valid.nunique())
    try:
        return pd.qcut(values, q=q, labels=labels[:q], duplicates="drop")
    except ValueError:
        return pd.Series(["bin_error"] * len(frame.index), index=frame.index, dtype=object)


def main() -> None:
    """执行误差切片分析。"""

    args = parse_args()
    errors_path = _resolve_path(args.errors)
    manifest_path = _resolve_path(args.manifest)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    errors = pd.read_csv(errors_path)
    manifest = pd.read_csv(manifest_path)
    merged = errors.merge(
        manifest[["flight", "task_mode", "task_config", "payload_g", "cruise_speed_mps", "altitude_m", "segment_count"]],
        on=["flight", "task_mode", "segment_count"],
        how="left",
    )

    task_rows = []
    for task_config in merged["task_config"].dropna().unique():
        task_path = Path(task_config)
        row = {"task_config": str(task_path)}
        row.update(_load_task_features(task_path))
        task_rows.append(row)
    task_features = pd.DataFrame(task_rows)
    merged = merged.merge(task_features, on="task_config", how="left")

    merged["abs_energy_error_pct"] = pd.to_numeric(merged["energy_error_pct"], errors="coerce").abs()
    merged["abs_range_error_pct"] = pd.to_numeric(merged["range_error_pct"], errors="coerce").abs()
    merged["speed_band"] = _bin_series(merged, "cruise_speed_mps", ["slow", "medium", "fast"])
    merged["distance_band"] = _bin_series(merged, "actual_total_distance_km", ["short", "medium", "long"])
    merged["tortuosity_band"] = _bin_series(merged, "route_tortuosity", ["straight", "mixed", "twisty"])
    merged["turn_band"] = _bin_series(merged, "route_total_heading_change_deg", ["low_turn", "mid_turn", "high_turn"])
    merged["altitude_band"] = _bin_series(merged, "route_altitude_range_m", ["flat", "mixed", "vertical"])

    merged.to_csv(output_dir / "task_replay_errors_enriched.csv", index=False)

    slice_columns = ["task_mode", "route", "speed_band", "distance_band", "tortuosity_band", "turn_band", "altitude_band"]
    slice_tables = {}
    for column in slice_columns:
        grouped = (
            merged.groupby(column, dropna=False)
            .agg(
                count=("flight", "count"),
                mean_abs_energy_error_pct=("abs_energy_error_pct", "mean"),
                median_abs_energy_error_pct=("abs_energy_error_pct", "median"),
                mean_abs_energy_error_wh=("abs_energy_error_wh", "mean"),
                mean_abs_range_error_pct=("abs_range_error_pct", "mean"),
            )
            .reset_index()
            .sort_values(["mean_abs_energy_error_pct", "mean_abs_energy_error_wh"], ascending=[False, False])
        )
        grouped.to_csv(output_dir / f"slice_{column}.csv", index=False)
        slice_tables[column] = str((output_dir / f"slice_{column}.csv").resolve())

    worst = merged.sort_values(["abs_energy_error_pct", "abs_energy_error_wh"], ascending=[False, False]).head(20)
    best = merged.sort_values(["abs_energy_error_pct", "abs_energy_error_wh"], ascending=[True, True]).head(20)
    worst.to_csv(output_dir / "worst_cases.csv", index=False)
    best.to_csv(output_dir / "best_cases.csv", index=False)

    polyline = merged[merged["task_mode"] == "polyline"].copy()
    endpoint = merged[merged["task_mode"] == "endpoint_only"].copy()
    summary = {
        "inputs": {
            "errors": str(errors_path.resolve()),
            "manifest": str(manifest_path.resolve()),
        },
        "row_count": int(len(merged.index)),
        "polyline_mean_abs_energy_error_pct": float(polyline["abs_energy_error_pct"].mean()) if not polyline.empty else None,
        "endpoint_mean_abs_energy_error_pct": float(endpoint["abs_energy_error_pct"].mean()) if not endpoint.empty else None,
        "polyline_mean_abs_energy_error_wh": float(polyline["abs_energy_error_wh"].mean()) if not polyline.empty else None,
        "endpoint_mean_abs_energy_error_wh": float(endpoint["abs_energy_error_wh"].mean()) if not endpoint.empty else None,
        "outputs": {
            "enriched": str((output_dir / "task_replay_errors_enriched.csv").resolve()),
            "worst_cases": str((output_dir / "worst_cases.csv").resolve()),
            "best_cases": str((output_dir / "best_cases.csv").resolve()),
            "slice_tables": slice_tables,
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(summary, output_dir / "summary.json")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
