# 从 M100 和 WEMUAV 等来源构建可训练表，并保留数据源审计信息。
"""构建多来源训练表。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_energy_engine.multi_source_training import build_multi_source_training_tables


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="构建多来源无人机能耗训练表。")
    parser.add_argument(
        "--m100-input",
        default="data/processed/flights_with_historical_weather_100m.csv",
        help="M100 逐时刻飞行日志 CSV",
    )
    parser.add_argument(
        "--wemuav-input",
        default="outputs/wemuav_dataset/wemuav_flights.csv",
        help="WEMUAV 统一逐时刻飞行日志 CSV",
    )
    parser.add_argument("--output-dir", default="outputs/multi_source_training", help="输出目录")
    parser.add_argument("--segment-seconds", type=float, default=60.0, help="分段长度，单位秒")
    parser.add_argument("--min-duration-s", type=float, default=10.0, help="最小分段时长，单位秒")
    parser.add_argument("--m100-min-distance-m", type=float, default=50.0, help="M100 最小分段距离")
    parser.add_argument("--wemuav-min-distance-m", type=float, default=0.1, help="WEMUAV 最小分段距离")
    parser.add_argument("--m100-route", default=None, help="可选 M100 路线过滤")
    parser.add_argument("--wemuav-route", default=None, help="可选 WEMUAV 工况过滤")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    args = parse_args()
    summary = build_multi_source_training_tables(
        output_dir=_resolve_path(args.output_dir),
        m100_input_csv=_resolve_path(args.m100_input),
        wemuav_input_csv=_resolve_path(args.wemuav_input),
        segment_seconds=args.segment_seconds,
        min_duration_s=args.min_duration_s,
        m100_min_distance_m=args.m100_min_distance_m,
        wemuav_min_distance_m=args.wemuav_min_distance_m,
        m100_route=args.m100_route,
        wemuav_route=args.wemuav_route,
    )
    print(
        json.dumps(
            {
                "output_dir": str(_resolve_path(args.output_dir)),
                "rows": summary["rows"],
                "source_counts": summary["source_counts"],
                "warning_count": summary["semantic_audit"]["warning_count"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
