# 构建分段级无人机能耗训练样本，用于天气影响建模和消融实验。
"""构建分段级能耗训练样本。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_energy_engine.dataset import build_segment_dataset


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="构建分段级能耗训练样本。")
    parser.add_argument("--input", default="data/processed/flights_with_historical_weather.csv", help="输入飞行日志 CSV")
    parser.add_argument("--output", default="outputs/segment_experiments/segment_features.csv", help="输出分段样本 CSV")
    parser.add_argument("--route", default="R1", help="可选路线过滤")
    parser.add_argument("--segment-seconds", type=float, default=60.0, help="分段长度，单位秒")
    parser.add_argument("--min-distance-m", type=float, default=50.0, help="最小分段距离，单位米")
    parser.add_argument("--min-duration-s", type=float, default=10.0, help="最小分段时长，单位秒")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out = build_segment_dataset(
        input_csv=ROOT / args.input if not Path(args.input).is_absolute() else Path(args.input),
        output_csv=ROOT / args.output if not Path(args.output).is_absolute() else Path(args.output),
        route=args.route or None,
        segment_seconds=args.segment_seconds,
        min_distance_m=args.min_distance_m,
        min_duration_s=args.min_duration_s,
    )
    print(f"segment_dataset rows={len(out)} cols={len(out.columns)} output={args.output}")
