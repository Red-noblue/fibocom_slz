"""构建训练样本与论文复现实验特征表的命令行入口。"""

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

from uav_energy_engine.dataset import build_research_feature_table, build_training_dataset


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="从 flights.csv 构建训练样本表。")
    parser.add_argument("--input", required=True, help="输入 flights.csv 路径")
    parser.add_argument("--output", default="outputs/features.csv", help="输出训练样本 CSV")
    parser.add_argument(
        "--research-output",
        default=None,
        help="可选：输出逐时刻论文复现特征表 CSV",
    )
    parser.add_argument("--route", default=None, help="可选路线过滤，例如 R1")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_training_dataset(args.input, args.output, args.route)
    if args.research_output:
        build_research_feature_table(args.input, args.research_output, args.route)
