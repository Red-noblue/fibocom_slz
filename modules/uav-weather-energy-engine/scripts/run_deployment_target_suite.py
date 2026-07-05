# 对比部署口径下“每公里能耗目标”和“分段总耗电目标”的训练与误差表现。
"""训练并评估不同能耗目标，判断部署模型应预测 Wh/km 还是分段 Wh。"""

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
from uav_energy_engine.error_analysis import (
    build_flight_error_table,
    build_segment_error_table,
    build_slice_error_table,
    summarize_error_tables,
)
from uav_energy_engine.evaluate import save_ablation_results, save_summary
from uav_energy_engine.model import WeatherEnergyModel, train_energy_model
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


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="对比部署模型的不同能耗预测目标。")
    parser.add_argument("--input", default="data/processed/flights_with_historical_weather_100m.csv", help="输入飞行日志 CSV")
    parser.add_argument("--route", default="R1", help="可选路线过滤")
    parser.add_argument("--output-dir", default="outputs/deployment_target_suite", help="实验输出目录")
    parser.add_argument("--segment-seconds", type=float, default=60.0, help="分段长度，单位秒")
    parser.add_argument("--min-distance-m", type=float, default=50.0, help="最小分段距离，单位米")
    parser.add_argument("--min-duration-s", type=float, default=10.0, help="最小分段时长，单位秒")
    parser.add_argument("--target-min", type=float, default=None, help="可选：按每公里能耗过滤异常分段的下限")
    parser.add_argument("--target-max", type=float, default=None, help="可选：按每公里能耗过滤异常分段的上限")
    parser.add_argument("--method", default="gradient_boosting", help="训练方法")
    parser.add_argument("--group-col", default="flight", help="训练/测试切分和飞行聚合使用的分组列")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    parser.add_argument("--battery-wh", type=float, default=130.0, help="可达性风险评估使用的电池容量 Wh")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _write_error_outputs(
    model_path: Path,
    features_csv: Path,
    target: str,
    variant_dir: Path,
    args: argparse.Namespace,
) -> dict:
    """输出单个目标模型的分段、飞行级和切片误差。"""

    model = WeatherEnergyModel.load(model_path)
    segment_errors, segment_meta = build_segment_error_table(
        model=model,
        features_csv=features_csv,
        target=target,
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
            "features_csv": str(features_csv.resolve()),
            "model_path": str(model_path.resolve()),
            "outputs": {
                "segment_errors": str((variant_dir / "segment_errors.csv").resolve()),
                "flight_errors": str((variant_dir / "flight_errors.csv").resolve()),
                "slice_errors": str((variant_dir / "slice_errors.csv").resolve()),
                "summary": str((variant_dir / "summary.json").resolve()),
            },
        }
    )
    segment_errors.to_csv(variant_dir / "segment_errors.csv", index=False)
    flight_errors.to_csv(variant_dir / "flight_errors.csv", index=False)
    slice_errors.to_csv(variant_dir / "slice_errors.csv", index=False)
    save_summary(summary, variant_dir / "summary.json")
    return summary


def _comparison_row(name: str, target: str, train_metrics: dict, summary: dict, variant_dir: Path) -> dict:
    """提取可横向比较的关键指标。"""

    segment = summary["segment"]
    flight = summary["flight"]
    risk = summary.get("risk", {})
    return {
        "variant": name,
        "target": target,
        "method": train_metrics["method"],
        "target_rmse": train_metrics["test"]["rmse"],
        "target_mae": train_metrics["test"]["mae"],
        "target_r2": train_metrics["test"]["r2"],
        "target_mode": segment.get("target_mode"),
        "segment_mean_abs_target_error_pct": segment.get("mean_abs_target_error_pct"),
        "segment_p95_abs_target_error_pct": segment.get("p95_abs_target_error_pct"),
        "segment_mean_abs_wh_per_km_error_pct": segment.get("mean_abs_error_wh_per_km_pct"),
        "segment_p95_abs_wh_per_km_error_pct": segment.get("p95_abs_error_wh_per_km_pct"),
        "flight_mean_abs_energy_error_wh": flight.get("mean_abs_energy_error_wh"),
        "flight_p95_abs_energy_error_wh": flight.get("p95_abs_energy_error_wh"),
        "flight_mean_abs_energy_error_pct": flight.get("mean_abs_energy_error_pct"),
        "flight_p95_abs_energy_error_pct": flight.get("p95_abs_energy_error_pct"),
        "range_mean_abs_error_km": flight.get("mean_abs_range_error_km"),
        "range_p95_abs_error_km": flight.get("p95_abs_range_error_km"),
        "range_mean_abs_error_pct": flight.get("mean_abs_range_error_pct"),
        "range_p95_abs_error_pct": flight.get("p95_abs_range_error_pct"),
        "range_overprediction_gt_25pct_count": risk.get("range_overprediction_gt_25pct_count"),
        "range_overprediction_gt_50pct_count": risk.get("range_overprediction_gt_50pct_count"),
        "range_overprediction_gt_100pct_count": risk.get("range_overprediction_gt_100pct_count"),
        "energy_underprediction_gt_25pct_count": risk.get("energy_underprediction_gt_25pct_count"),
        "energy_underprediction_gt_50pct_count": risk.get("energy_underprediction_gt_50pct_count"),
        "train_count": train_metrics["train"]["count"],
        "test_count": train_metrics["test"]["count"],
        "feature_count": len(train_metrics["features"]),
        "metrics_path": str((variant_dir / "metrics.json").resolve()),
        "model_path": str((variant_dir / "model.pkl").resolve()),
        "summary_path": str((variant_dir / "summary.json").resolve()),
    }


def _train_and_evaluate_variant(
    name: str,
    target: str,
    features_csv: Path,
    feature_cols: list[str],
    output_dir: Path,
    args: argparse.Namespace,
) -> dict:
    """训练并评估一个部署目标版本。"""

    variant_dir = output_dir / name
    variant_dir.mkdir(parents=True, exist_ok=True)
    model_path = variant_dir / "model.pkl"
    train_metrics = train_energy_model(
        features_csv=features_csv,
        model_out=model_path,
        metrics_out=variant_dir / "metrics.json",
        random_state=args.random_state,
        method=args.method,
        target=target,
        feature_cols=feature_cols,
        base_cols=CORE_FLIGHT_FEATURES,
        test_size=args.test_size,
        group_col=args.group_col,
    )
    error_summary = _write_error_outputs(
        model_path=model_path,
        features_csv=features_csv,
        target=target,
        variant_dir=variant_dir,
        args=args,
    )
    return _comparison_row(name, target, train_metrics, error_summary, variant_dir)


def main() -> None:
    """执行目标口径对比实验。"""

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

    feature_cols = CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES
    variants = [
        ("preflight_rate_target", "segment_wh_per_km"),
        ("preflight_energy_target", "segment_energy_wh"),
    ]
    rows = [
        _train_and_evaluate_variant(name, target, preflight_csv, feature_cols, output_dir, args)
        for name, target in variants
    ]
    best_by_energy_pct = min(rows, key=lambda row: row["flight_mean_abs_energy_error_pct"])
    best_by_range_p95 = min(rows, key=lambda row: row["range_p95_abs_error_pct"])
    payload = {
        "input": str(_resolve_path(args.input)),
        "route": args.route,
        "segment_seconds": args.segment_seconds,
        "min_distance_m": args.min_distance_m,
        "min_duration_s": args.min_duration_s,
        "filter": filter_meta,
        "method": args.method,
        "group_col": args.group_col,
        "test_size": args.test_size,
        "battery_wh": args.battery_wh,
        "views": {
            "onboard": str(segment_csv.resolve()),
            "preflight": str(preflight_csv.resolve()),
        },
        "results": rows,
        "best_by_flight_mean_abs_energy_error_pct": best_by_energy_pct,
        "best_by_range_p95_abs_error_pct": best_by_range_p95,
    }
    save_ablation_results(rows, output_dir / "comparison.csv")
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
