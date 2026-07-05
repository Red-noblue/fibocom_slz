# 分析 M100 原始 60 秒窗口在训练/回放构建时的保留与过滤情况，定位任务过程丢失来源。
"""分析 M100 分段窗口保留率。"""

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

import numpy as np
import pandas as pd

from uav_energy_engine.dataset import (
    SEGMENT_OPTIONAL_NUMERIC_COLUMNS,
    SEGMENT_OPTIONAL_TEXT_COLUMNS,
    SEGMENT_REQUIRED_COLUMNS,
    _prepare_feature_frame,
    aggregate_segment,
)
from uav_energy_engine.evaluate import save_summary


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="分析 M100 任务分段窗口保留与过滤情况。")
    parser.add_argument(
        "--input",
        default="data/processed/flights_with_historical_weather.csv",
        help="逐时刻飞行日志",
    )
    parser.add_argument(
        "--segment-seconds",
        type=float,
        default=60.0,
        help="窗口长度，单位秒",
    )
    parser.add_argument(
        "--min-distance-m",
        type=float,
        default=50.0,
        help="分段最小距离阈值",
    )
    parser.add_argument(
        "--min-duration-s",
        type=float,
        default=10.0,
        help="分段最小时长阈值",
    )
    parser.add_argument(
        "--route-prefix",
        default="R",
        help="仅分析指定前缀路线，例如 R 代表 R1~R7",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/m100_window_retention_analysis",
        help="输出目录",
    )
    return parser.parse_args()


def main() -> None:
    """执行窗口保留分析。"""

    args = parse_args()
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    usecols = SEGMENT_REQUIRED_COLUMNS + SEGMENT_OPTIONAL_NUMERIC_COLUMNS + SEGMENT_OPTIONAL_TEXT_COLUMNS
    frame = _prepare_feature_frame(_resolve_path(args.input), usecols)
    if args.route_prefix:
        frame = frame[frame["route"].astype(str).str.startswith(str(args.route_prefix))].copy()

    per_window_rows = []
    per_flight_rows = []

    for flight_id, flight_group in frame.groupby("flight", sort=True):
        flight_group = flight_group.sort_values("time").copy()
        min_time = float(pd.to_numeric(flight_group["time"], errors="coerce").min())
        relative_time = pd.to_numeric(flight_group["time"], errors="coerce") - min_time
        flight_group = flight_group.assign(segment_id=np.floor(relative_time / float(args.segment_seconds)).astype("Int64"))
        route_name = str(flight_group["route"].iloc[0])

        total_windows = 0
        kept_windows = 0
        dropped_distance = 0
        dropped_duration = 0
        dropped_invalid = 0
        dropped_hover_like = 0

        for segment_id, segment_group in flight_group.groupby("segment_id"):
            if pd.isna(segment_id):
                continue
            total_windows += 1
            row = aggregate_segment(
                segment_group,
                int(segment_id),
                float(int(segment_id) * float(args.segment_seconds)),
                float(args.segment_seconds),
            )
            if not row:
                dropped_invalid += 1
                per_window_rows.append(
                    {
                        "flight": int(flight_id),
                        "route": route_name,
                        "segment_id": int(segment_id),
                        "kept": False,
                        "drop_reason": "invalid",
                    }
                )
                continue

            keep_distance = float(row["distance_m"]) >= float(args.min_distance_m)
            keep_duration = float(row["duration_s"]) >= float(args.min_duration_s)
            kept = bool(keep_distance and keep_duration)
            if kept:
                kept_windows += 1
                drop_reason = ""
            else:
                reasons = []
                if not keep_distance:
                    dropped_distance += 1
                    reasons.append("short_distance")
                if not keep_duration:
                    dropped_duration += 1
                    reasons.append("short_duration")
                if str(row.get("phase_label", "")) == "hover_or_slow":
                    dropped_hover_like += 1
                drop_reason = "+".join(reasons) or "filtered"

            per_window_rows.append(
                {
                    "flight": int(flight_id),
                    "route": route_name,
                    "segment_id": int(segment_id),
                    "segment_start_s": float(row.get("segment_start_s", np.nan)),
                    "duration_s": float(row.get("duration_s", np.nan)),
                    "distance_m": float(row.get("distance_m", np.nan)),
                    "phase_label": str(row.get("phase_label", "")),
                    "segment_wh_per_km": float(row.get("segment_wh_per_km", np.nan)),
                    "kept": kept,
                    "drop_reason": drop_reason,
                }
            )

        total_duration_s = float(pd.to_numeric(flight_group["time"], errors="coerce").max() - min_time)
        per_flight_rows.append(
            {
                "flight": int(flight_id),
                "route": route_name,
                "raw_sample_count": int(len(flight_group.index)),
                "raw_duration_s": total_duration_s,
                "window_count": int(total_windows),
                "kept_window_count": int(kept_windows),
                "kept_window_ratio": float(kept_windows / total_windows) if total_windows else float("nan"),
                "dropped_distance_count": int(dropped_distance),
                "dropped_duration_count": int(dropped_duration),
                "dropped_invalid_count": int(dropped_invalid),
                "dropped_hover_like_count": int(dropped_hover_like),
            }
        )

    per_window = pd.DataFrame(per_window_rows)
    per_flight = pd.DataFrame(per_flight_rows)
    per_window.to_csv(output_dir / "window_rows.csv", index=False)
    per_flight.to_csv(output_dir / "flight_retention.csv", index=False)

    route_summary = (
        per_flight.groupby("route", dropna=False)
        .agg(
            flight_count=("flight", "count"),
            mean_window_count=("window_count", "mean"),
            mean_kept_window_count=("kept_window_count", "mean"),
            mean_kept_window_ratio=("kept_window_ratio", "mean"),
        )
        .reset_index()
        .sort_values("mean_kept_window_ratio")
    )
    route_summary.to_csv(output_dir / "route_retention.csv", index=False)

    drop_reason_summary = (
        per_window[~per_window["kept"]]
        .groupby(["route", "drop_reason"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["route", "count"], ascending=[True, False])
    )
    drop_reason_summary.to_csv(output_dir / "drop_reason_summary.csv", index=False)

    summary = {
        "input": str(_resolve_path(args.input).resolve()),
        "flight_count": int(len(per_flight.index)),
        "window_count": int(len(per_window.index)),
        "mean_window_count": float(per_flight["window_count"].mean()),
        "mean_kept_window_count": float(per_flight["kept_window_count"].mean()),
        "mean_kept_window_ratio": float(per_flight["kept_window_ratio"].mean()),
        "single_kept_window_flights": int((per_flight["kept_window_count"] == 1).sum()),
        "outputs": {
            "flight_retention": str((output_dir / "flight_retention.csv").resolve()),
            "window_rows": str((output_dir / "window_rows.csv").resolve()),
            "route_retention": str((output_dir / "route_retention.csv").resolve()),
            "drop_reason_summary": str((output_dir / "drop_reason_summary.csv").resolve()),
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(summary, output_dir / "summary.json")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
