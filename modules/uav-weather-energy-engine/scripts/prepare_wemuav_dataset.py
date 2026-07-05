"""将 WEMUAV 数据集整理为统一 flights.csv 的命令行入口。"""

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

from uav_energy_engine.wemuav_dataset import prepare_wemuav_dataset


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="整理 WEMUAV 数据集为统一 flights.csv。")
    parser.add_argument("--dataset-root", required=True, help="数据集根目录，应包含 01_DATA_OVERVIEW.csv")
    parser.add_argument("--output", default="data/raw/wemuav_flights.csv", help="输出 flights.csv 路径")
    parser.add_argument("--overview", default=None, help="可选：显式指定 overview CSV 路径")
    parser.add_argument("--flight-id-offset", type=int, default=1_000_000, help="飞行编号偏移，避免与其他数据源冲突")
    parser.add_argument("--max-cases", type=int, default=None, help="可选：仅处理前 N 条任务记录，便于调试")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out = prepare_wemuav_dataset(
        dataset_root=args.dataset_root,
        output_csv=args.output,
        overview_csv=args.overview,
        flight_id_offset=args.flight_id_offset,
        max_cases=args.max_cases,
    )
    print(
        "wemuav_dataset rows={} flights={} output={}".format(
            len(out.index),
            int(out["flight"].nunique()),
            args.output,
        )
    )
