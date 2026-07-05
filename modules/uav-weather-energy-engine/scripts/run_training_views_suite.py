# 对比机载上限模型与飞行前天气部署模型，验证训练字段和运行字段是否一致。
"""训练并对比不同数据视图下的能耗模型。"""

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

from uav_energy_engine.dataset import build_segment_dataset, filter_segment_outliers
from uav_energy_engine.evaluate import save_ablation_results, save_summary
from uav_energy_engine.model import train_energy_model
from uav_energy_engine.route_features import build_preflight_training_feature_view


CORE_FLIGHT_FEATURES = [
    "planned_ground_speed_mps",
    "payload_kg",
    "altitude_m",
    "distance_m",
    "duration_s",
    "heading_deg",
]

PREFLIGHT_WEATHER_FEATURES = [
    "wind_speed_mps",
    "headwind_mps",
    "crosswind_mps",
    "wind_gust_mps",
    "temperature_c",
    "relative_humidity_pct",
    "pressure_hpa",
    "precipitation_mm",
    "air_density_kgm3",
]

ONBOARD_CEILING_FEATURES = [
    "wind_speed_mps",
    "headwind_mps",
    "crosswind_mps",
    "wind_speed_max",
    "wind_speed_std",
    "wind_speed_p95",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="训练机载上限模型与飞行前天气部署模型。")
    parser.add_argument("--input", default="data/processed/flights_with_historical_weather_100m.csv", help="输入飞行日志 CSV")
    parser.add_argument("--route", default="R1", help="可选路线过滤")
    parser.add_argument("--output-dir", default="outputs/training_views_suite", help="实验输出目录")
    parser.add_argument("--segment-seconds", type=float, default=60.0, help="分段长度，单位秒")
    parser.add_argument("--min-distance-m", type=float, default=50.0, help="最小分段距离，单位米")
    parser.add_argument("--min-duration-s", type=float, default=10.0, help="最小分段时长，单位秒")
    parser.add_argument("--target-min", type=float, default=None, help="分段每公里能耗下限")
    parser.add_argument("--target-max", type=float, default=None, help="分段每公里能耗上限")
    parser.add_argument("--method", default="gradient_boosting", help="训练方法")
    parser.add_argument("--group-col", default="flight", help="训练/测试切分使用的分组列")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _train_variant(
    name: str,
    features_csv: Path,
    feature_cols: list[str],
    args: argparse.Namespace,
    output_dir: Path,
) -> dict:
    """训练单个数据视图模型并返回汇总行。"""

    variant_dir = output_dir / name
    metrics = train_energy_model(
        features_csv=features_csv,
        model_out=variant_dir / "model.pkl",
        metrics_out=variant_dir / "metrics.json",
        random_state=args.random_state,
        method=args.method,
        target="segment_wh_per_km",
        feature_cols=feature_cols,
        base_cols=CORE_FLIGHT_FEATURES,
        test_size=args.test_size,
        group_col=args.group_col,
    )
    return {
        "variant": name,
        "method": args.method,
        "view_csv": str(features_csv.resolve()),
        "feature_count": len(metrics["features"]),
        "features": ",".join(metrics["features"]),
        "test_mae": metrics["test"]["mae"],
        "test_rmse": metrics["test"]["rmse"],
        "test_r2": metrics["test"]["r2"],
        "test_naive_rmse": metrics["test"]["naive_rmse"],
        "train_count": metrics["train"]["count"],
        "test_count": metrics["test"]["count"],
        "split_strategy": metrics.get("split_strategy"),
        "group_col": metrics.get("group_col"),
        "total_group_count": metrics.get("total_group_count"),
        "train_group_count": metrics.get("train_group_count"),
        "test_group_count": metrics.get("test_group_count"),
        "metrics_path": str((variant_dir / "metrics.json").resolve()),
        "model_path": str((variant_dir / "model.pkl").resolve()),
    }


def main() -> None:
    """执行训练视图对比。"""

    args = parse_args()
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    segment_csv = output_dir / "segment_features_onboard.csv"
    segment_frame = build_segment_dataset(
        input_csv=_resolve_path(args.input),
        output_csv=segment_csv,
        route=args.route or None,
        segment_seconds=args.segment_seconds,
        min_distance_m=args.min_distance_m,
        min_duration_s=args.min_duration_s,
    )
    filter_meta = None
    if args.target_min is not None or args.target_max is not None:
        segment_frame, filter_meta = filter_segment_outliers(
            segment_frame,
            target_col="segment_wh_per_km",
            min_target=args.target_min,
            max_target=args.target_max,
        )
        segment_frame.to_csv(segment_csv, index=False)

    preflight_csv = output_dir / "segment_features_preflight.csv"
    preflight_frame = build_preflight_training_feature_view(segment_frame)
    preflight_frame.to_csv(preflight_csv, index=False)

    variants = [
        ("task_only", segment_csv, CORE_FLIGHT_FEATURES),
        ("onboard_ceiling", segment_csv, CORE_FLIGHT_FEATURES + ONBOARD_CEILING_FEATURES),
        ("preflight_weather_deployment", preflight_csv, CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES),
    ]

    rows = [
        _train_variant(name, features_csv, feature_cols, args, output_dir)
        for name, features_csv, feature_cols in variants
    ]
    best_row = min(rows, key=lambda row: row["test_rmse"])
    payload = {
        "input": str(_resolve_path(args.input)),
        "route": args.route,
        "segment_seconds": args.segment_seconds,
        "min_distance_m": args.min_distance_m,
        "min_duration_s": args.min_duration_s,
        "filter": filter_meta,
        "target": "segment_wh_per_km",
        "method": args.method,
        "group_col": args.group_col,
        "test_size": args.test_size,
        "views": {
            "onboard": str(segment_csv.resolve()),
            "preflight": str(preflight_csv.resolve()),
        },
        "results": rows,
        "best_by_rmse": best_row,
    }
    save_ablation_results(rows, output_dir / "comparison.csv")
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(best_row, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
