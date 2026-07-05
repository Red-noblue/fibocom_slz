# 执行分段级天气消融实验，用于验证天气特征是否提升分段能耗预测。
"""执行分段级天气消融实验。"""

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


TASK_FEATURES = ["planned_ground_speed_mps", "payload_kg", "altitude_m", "distance_m", "duration_s"]
ARCHIVE_WEATHER_FEATURES = [
    "hist_wind_speed_mps",
    "hist_wind_speed_100m_mps",
    "hist_height_wind_speed_mps",
    "hist_headwind_mps",
    "hist_crosswind_mps",
    "hist_wind_gust_mps",
    "hist_relative_humidity_pct",
    "hist_temperature_c",
    "hist_pressure_hpa",
    "hist_precipitation_mm",
    "hist_air_density_kgm3",
    "hist_wind_speed_mps_max",
    "hist_wind_speed_mps_std",
    "hist_wind_speed_100m_mps_max",
    "hist_wind_speed_100m_mps_std",
    "hist_wind_gust_mps_max",
    "hist_temperature_c_std",
    "hist_pressure_hpa_std",
]
ONBOARD_WIND_FEATURES = [
    "wind_speed_mps",
    "headwind_mps",
    "crosswind_mps",
    "wind_speed_max",
    "wind_speed_std",
    "wind_speed_p95",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="执行分段级天气消融实验。")
    parser.add_argument("--input", default="data/processed/flights_with_historical_weather.csv", help="输入飞行日志 CSV")
    parser.add_argument("--route", default="R1", help="可选路线过滤")
    parser.add_argument("--output-dir", default="outputs/segment_experiments", help="实验输出目录")
    parser.add_argument("--segment-seconds", type=float, default=60.0, help="分段长度，单位秒")
    parser.add_argument("--min-distance-m", type=float, default=50.0, help="最小分段距离，单位米")
    parser.add_argument("--min-duration-s", type=float, default=10.0, help="最小分段时长，单位秒")
    parser.add_argument("--target-min", type=float, default=None, help="分段每公里能耗下限")
    parser.add_argument("--target-max", type=float, default=None, help="分段每公里能耗上限")
    parser.add_argument("--target-lower-quantile", type=float, default=None, help="按分位数计算能耗下限")
    parser.add_argument("--target-upper-quantile", type=float, default=None, help="按分位数计算能耗上限")
    parser.add_argument("--method", default="gradient_boosting", help="训练方法")
    parser.add_argument("--group-col", default="flight", help="训练/测试切分使用的分组列")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    return parser.parse_args()


def variant_feature_map() -> dict:
    """返回分段消融实验的特征组合。"""

    return {
        "task_only": TASK_FEATURES,
        "task_plus_archive_weather": TASK_FEATURES + ARCHIVE_WEATHER_FEATURES,
        "task_plus_onboard_wind": TASK_FEATURES + ONBOARD_WIND_FEATURES,
        "task_plus_all_weather": TASK_FEATURES + ARCHIVE_WEATHER_FEATURES + ONBOARD_WIND_FEATURES,
    }


def main() -> None:
    """执行分段消融实验主流程。"""

    args = parse_args()
    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    segment_features_csv = output_dir / "segment_features.csv"
    segment_frame = build_segment_dataset(
        input_csv=ROOT / args.input if not Path(args.input).is_absolute() else Path(args.input),
        output_csv=segment_features_csv,
        route=args.route or None,
        segment_seconds=args.segment_seconds,
        min_distance_m=args.min_distance_m,
        min_duration_s=args.min_duration_s,
    )
    filter_meta = None
    if (
        args.target_min is not None
        or args.target_max is not None
        or args.target_lower_quantile is not None
        or args.target_upper_quantile is not None
    ):
        segment_frame, filter_meta = filter_segment_outliers(
            segment_frame,
            target_col="segment_wh_per_km",
            min_target=args.target_min,
            max_target=args.target_max,
            lower_quantile=args.target_lower_quantile,
            upper_quantile=args.target_upper_quantile,
        )
        segment_frame.to_csv(segment_features_csv, index=False)

    rows = []
    best_row = None
    for variant, feature_cols in variant_feature_map().items():
        variant_dir = output_dir / variant
        metrics = train_energy_model(
            features_csv=segment_features_csv,
            model_out=variant_dir / "model.pkl",
            metrics_out=variant_dir / "metrics.json",
            random_state=args.random_state,
            method=args.method,
            target="segment_wh_per_km",
            feature_cols=feature_cols,
            base_cols=TASK_FEATURES,
            test_size=args.test_size,
            group_col=args.group_col,
        )
        row = {
            "variant": variant,
            "method": args.method,
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
        rows.append(row)
        if best_row is None or row["test_rmse"] < best_row["test_rmse"]:
            best_row = row

    payload = {
        "input_csv": str(segment_features_csv.resolve()),
        "route": args.route,
        "segment_seconds": args.segment_seconds,
        "target": "segment_wh_per_km",
        "method": args.method,
        "group_col": args.group_col,
        "test_size": args.test_size,
        "filter": filter_meta,
        "results": rows,
        "best_by_rmse": best_row,
    }
    save_ablation_results(rows, output_dir / "comparison.csv")
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload["best_by_rmse"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
