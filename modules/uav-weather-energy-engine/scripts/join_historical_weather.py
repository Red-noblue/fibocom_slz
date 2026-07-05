"""将历史天气按飞行时刻回填到飞行日志的命令行入口。"""

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

from uav_energy_engine.weather import join_historical_weather


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="将历史天气回填到飞行日志。")
    parser.add_argument("--input", required=True, help="输入 flights.csv 路径")
    parser.add_argument("--output", required=True, help="输出带历史天气的 flights.csv 路径")
    parser.add_argument(
        "--weather-config",
        default="configs/historical_weather.yaml",
        help="历史天气接口配置文件",
    )
    parser.add_argument("--route", default=None, help="可选：仅处理指定路线")
    parser.add_argument("--timezone", default="America/New_York", help="本地时区")
    parser.add_argument("--cache-precision", type=int, default=2, help="天气缓存经纬度保留位数")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out = join_historical_weather(
        input_csv=args.input,
        output_csv=args.output,
        weather_config=args.weather_config,
        route=args.route,
        timezone=args.timezone,
        cache_precision=args.cache_precision,
    )
    print(
        "historical_weather_join rows={} cols={} output={}".format(
            len(out.index),
            len(out.columns),
            args.output,
        )
    )
