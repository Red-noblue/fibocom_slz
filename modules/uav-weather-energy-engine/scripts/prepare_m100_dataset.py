"""将公开 M100 数据集整理为引擎统一 flights.csv 的命令行入口。"""

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

from uav_energy_engine.dataset import prepare_m100_dataset


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="整理公开 M100 数据集为统一 flights.csv。")
    parser.add_argument("--dataset-root", required=True, help="数据集根目录，应包含 parameters.csv")
    parser.add_argument("--output", default="data/raw/flights.csv", help="输出 flights.csv 路径")
    parser.add_argument("--flights-zip", default=None, help="可选：显式指定 flights.zip 路径")
    parser.add_argument("--parameters", default=None, help="可选：显式指定 parameters.csv 路径")
    parser.add_argument("--flight-id-offset", type=int, default=0, help="飞行编号偏移，避免与其他数据源冲突")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    prepare_m100_dataset(
        dataset_root=args.dataset_root,
        output_csv=args.output,
        flights_zip=args.flights_zip,
        parameters_csv=args.parameters,
        flight_id_offset=args.flight_id_offset,
    )
