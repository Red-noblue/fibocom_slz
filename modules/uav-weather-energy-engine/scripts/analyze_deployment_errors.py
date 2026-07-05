# 分析飞行前部署模型误差，输出分段误差、飞行级误差和场景切片表。
"""分析部署模型误差。"""

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

from uav_energy_engine.error_analysis import (
    build_flight_error_table,
    build_segment_error_table,
    build_slice_error_table,
    summarize_error_tables,
)
from uav_energy_engine.evaluate import save_summary
from uav_energy_engine.model import WeatherEnergyModel


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="分析飞行前部署模型误差。")
    parser.add_argument("--features", default="outputs/training_views_suite/segment_features_preflight.csv", help="部署口径特征 CSV")
    parser.add_argument("--model", default="outputs/training_views_suite/preflight_weather_deployment/model.pkl", help="模型文件")
    parser.add_argument("--output-dir", default="outputs/deployment_error_analysis", help="分析输出目录")
    parser.add_argument("--target", default="segment_wh_per_km", help="预测目标列")
    parser.add_argument("--group-col", default="flight", help="测试切分和飞行聚合使用的分组列")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--battery-wh", type=float, default=130.0, help="可达性风险评估使用的电池容量 Wh")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    """执行误差分析。"""

    args = parse_args()
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model = WeatherEnergyModel.load(_resolve_path(args.model))
    segment_errors, segment_meta = build_segment_error_table(
        model=model,
        features_csv=_resolve_path(args.features),
        target=args.target,
        test_size=args.test_size,
        random_state=args.random_state,
        group_col=args.group_col,
    )
    flight_errors = build_flight_error_table(
        segment_errors,
        battery_wh=args.battery_wh,
        group_col=args.group_col,
    )
    slice_errors = build_slice_error_table(segment_errors)
    summary = summarize_error_tables(
        segment_errors=segment_errors,
        flight_errors=flight_errors,
        segment_meta=segment_meta,
        battery_wh=args.battery_wh,
    )
    summary.update(
        {
            "features_csv": str(_resolve_path(args.features)),
            "model_path": str(_resolve_path(args.model)),
            "outputs": {
                "segment_errors": str((output_dir / "segment_errors.csv").resolve()),
                "flight_errors": str((output_dir / "flight_errors.csv").resolve()),
                "slice_errors": str((output_dir / "slice_errors.csv").resolve()),
                "summary": str((output_dir / "summary.json").resolve()),
            },
        }
    )

    segment_errors.to_csv(output_dir / "segment_errors.csv", index=False)
    flight_errors.to_csv(output_dir / "flight_errors.csv", index=False)
    slice_errors.to_csv(output_dir / "slice_errors.csv", index=False)
    save_summary(summary, output_dir / "summary.json")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
