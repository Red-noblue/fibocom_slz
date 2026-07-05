# 从跨路线泛化误差生成保守可达性安全校准文件。
"""生成 P50/P90/P95 能耗安全裕度配置。"""

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

from uav_energy_engine.reachability import build_reachability_safety_profile, save_reachability_safety_profile


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="根据飞行级泛化误差生成保守可达性校准文件。")
    parser.add_argument(
        "--flight-errors",
        default="outputs/generalization_benchmark_route_geometry/route_holdout/flight_errors.csv",
        help="飞行级误差 CSV，建议使用跨路线留出结果",
    )
    parser.add_argument("--output", default="outputs/reachability_safety_profile.json", help="输出 JSON 路径")
    parser.add_argument("--source-name", default=None, help="校准来源说明")
    parser.add_argument("--quantiles", nargs="+", type=float, default=[0.5, 0.9, 0.95], help="要输出的分位数")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    """执行安全校准文件生成。"""

    args = parse_args()
    flight_errors = _resolve_path(args.flight_errors)
    source_name = args.source_name or str(flight_errors)
    profile = build_reachability_safety_profile(
        flight_errors=flight_errors,
        quantiles=args.quantiles,
        source_name=source_name,
    )
    output_path = save_reachability_safety_profile(profile, _resolve_path(args.output))
    payload = {"output": str(output_path.resolve()), **profile}
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
