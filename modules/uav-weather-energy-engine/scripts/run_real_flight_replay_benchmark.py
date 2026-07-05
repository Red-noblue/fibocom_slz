# 对真实飞行日志做回放基准评估，比较不同分段长度和能耗目标定义。
"""运行真实飞行回放基准实验。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


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
from uav_energy_engine.target_modes import infer_target_mode


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

PHASE_AND_DYNAMIC_FEATURES = [
    "climb_ratio",
    "descent_ratio",
    "level_ratio",
    "turn_ratio",
    "hover_or_slow_ratio",
    "cruise_ratio",
    "altitude_delta_m",
    "altitude_range_m",
    "altitude_gain_m",
    "altitude_loss_m",
    "vertical_speed_mean_mps",
    "vertical_speed_abs_mean_mps",
    "vertical_speed_abs_p95_mps",
    "horizontal_speed_mean_mps",
    "horizontal_speed_std_mps",
    "horizontal_speed_p95_mps",
    "acceleration_abs_mean_mps2",
    "acceleration_abs_p95_mps2",
    "turn_rate_mean_deg_s",
    "turn_rate_p95_deg_s",
]

DEFAULT_TARGETS = [
    "segment_wh_per_km",
    "segment_energy_wh",
    "segment_wh_per_s",
    "mean_power_w",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="比较真实飞行回放下的分段长度和目标定义。")
    parser.add_argument("--input", default="data/processed/flights_with_historical_weather_100m.csv", help="输入飞行日志 CSV")
    parser.add_argument("--route", default="R1", help="可选路线过滤")
    parser.add_argument("--output-dir", default="outputs/real_flight_replay_benchmark", help="实验输出目录")
    parser.add_argument("--segment-seconds", type=float, nargs="+", default=[60.0, 120.0, 180.0], help="要比较的分段秒数")
    parser.add_argument("--targets", nargs="+", default=DEFAULT_TARGETS, help="要比较的预测目标列")
    parser.add_argument("--min-distance-m", type=float, default=None, help="固定最小分段距离；不填则按分段秒数推断")
    parser.add_argument("--min-duration-s", type=float, default=None, help="固定最小分段时长；不填则按分段秒数推断")
    parser.add_argument("--min-distance-mps", type=float, default=0.833333, help="自动最小分段距离系数，单位 m/s")
    parser.add_argument("--min-duration-ratio", type=float, default=0.25, help="自动最小分段时长占分段秒数的比例")
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


def _safe_name(value: str) -> str:
    """把参数值转换为安全目录名。"""

    return str(value).replace("/", "_").replace(".", "p")


def _auto_min_distance_m(segment_seconds: float, args: argparse.Namespace) -> float:
    """计算自动最小分段距离。"""

    if args.min_distance_m is not None:
        return float(args.min_distance_m)
    return max(1.0, float(segment_seconds) * float(args.min_distance_mps))


def _auto_min_duration_s(segment_seconds: float, args: argparse.Namespace) -> float:
    """计算自动最小分段时长。"""

    if args.min_duration_s is not None:
        return float(args.min_duration_s)
    return max(10.0, float(segment_seconds) * float(args.min_duration_ratio))


def _add_derived_targets(frame: pd.DataFrame) -> pd.DataFrame:
    """补充 Wh/s 和平均功率 W 等目标列。"""

    out = frame.copy()
    energy_wh = pd.to_numeric(out["segment_energy_wh"], errors="coerce")
    duration_s = pd.to_numeric(out["duration_s"], errors="coerce")
    valid = duration_s > 1e-9
    out["segment_wh_per_s"] = np.nan
    out["mean_power_w"] = np.nan
    out.loc[valid, "segment_wh_per_s"] = energy_wh.loc[valid] / duration_s.loc[valid]
    out.loc[valid, "mean_power_w"] = energy_wh.loc[valid] * 3600.0 / duration_s.loc[valid]
    return out


def _write_error_outputs(
    model_path: Path,
    features_csv: Path,
    target: str,
    variant_dir: Path,
    args: argparse.Namespace,
) -> dict:
    """输出单个模型的分段、飞行级和切片误差。"""

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


def _comparison_row(
    segment_seconds: float,
    min_distance_m: float,
    min_duration_s: float,
    target: str,
    train_metrics: dict,
    summary: dict,
    variant_dir: Path,
) -> dict:
    """提取横向比较指标。"""

    segment = summary["segment"]
    flight = summary["flight"]
    risk = summary.get("risk", {})
    return {
        "segment_seconds": float(segment_seconds),
        "min_distance_m": float(min_distance_m),
        "min_duration_s": float(min_duration_s),
        "target": target,
        "target_mode": segment.get("target_mode") or infer_target_mode(target),
        "method": train_metrics["method"],
        "target_rmse": train_metrics["test"]["rmse"],
        "target_mae": train_metrics["test"]["mae"],
        "target_r2": train_metrics["test"]["r2"],
        "segment_count": segment.get("count"),
        "flight_count": flight.get("count"),
        "segment_mean_abs_target_error_pct": segment.get("mean_abs_target_error_pct"),
        "segment_p95_abs_target_error_pct": segment.get("p95_abs_target_error_pct"),
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
        "model_path": str((variant_dir / "model.pkl").resolve()),
        "summary_path": str((variant_dir / "summary.json").resolve()),
    }


def _train_and_evaluate_target(
    target: str,
    features_csv: Path,
    segment_seconds: float,
    min_distance_m: float,
    min_duration_s: float,
    segment_dir: Path,
    args: argparse.Namespace,
) -> dict:
    """训练并评估单个目标定义。"""

    variant_dir = segment_dir / _safe_name(target)
    variant_dir.mkdir(parents=True, exist_ok=True)
    model_path = variant_dir / "model.pkl"
    feature_cols = CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES + PHASE_AND_DYNAMIC_FEATURES
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
    return _comparison_row(
        segment_seconds=segment_seconds,
        min_distance_m=min_distance_m,
        min_duration_s=min_duration_s,
        target=target,
        train_metrics=train_metrics,
        summary=error_summary,
        variant_dir=variant_dir,
    )


def _prepare_segment_view(segment_seconds: float, args: argparse.Namespace, output_dir: Path) -> tuple[Path, dict]:
    """按指定分段长度生成部署口径特征表。"""

    min_distance_m = _auto_min_distance_m(segment_seconds, args)
    min_duration_s = _auto_min_duration_s(segment_seconds, args)
    segment_dir = output_dir / f"segments_{int(round(segment_seconds))}s"
    segment_dir.mkdir(parents=True, exist_ok=True)

    onboard_csv = segment_dir / "segment_features_onboard.csv"
    onboard_frame = build_segment_dataset(
        input_csv=_resolve_path(args.input),
        output_csv=onboard_csv,
        route=args.route or None,
        segment_seconds=segment_seconds,
        min_distance_m=min_distance_m,
        min_duration_s=min_duration_s,
    )
    filter_meta = None
    if args.target_min is not None or args.target_max is not None:
        onboard_frame, filter_meta = filter_segment_outliers(
            onboard_frame,
            target_col="segment_wh_per_km",
            min_target=args.target_min,
            max_target=args.target_max,
        )
        onboard_frame.to_csv(onboard_csv, index=False)

    preflight_csv = segment_dir / "segment_features_preflight.csv"
    preflight_frame = build_preflight_training_feature_view(onboard_frame)
    preflight_frame = _add_derived_targets(preflight_frame)
    preflight_frame.to_csv(preflight_csv, index=False)
    meta = {
        "segment_seconds": float(segment_seconds),
        "min_distance_m": float(min_distance_m),
        "min_duration_s": float(min_duration_s),
        "filter": filter_meta,
        "segment_dir": str(segment_dir.resolve()),
        "onboard_csv": str(onboard_csv.resolve()),
        "preflight_csv": str(preflight_csv.resolve()),
        "row_count": int(len(preflight_frame.index)),
        "flight_count": int(preflight_frame[args.group_col].nunique()) if args.group_col in preflight_frame.columns else None,
    }
    return preflight_csv, meta


def main() -> None:
    """执行真实飞行回放基准实验。"""

    args = parse_args()
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    segment_views = []
    for segment_seconds in args.segment_seconds:
        features_csv, segment_meta = _prepare_segment_view(segment_seconds, args, output_dir)
        segment_views.append(segment_meta)
        segment_dir = Path(segment_meta["segment_dir"])
        for target in args.targets:
            rows.append(
                _train_and_evaluate_target(
                    target=target,
                    features_csv=features_csv,
                    segment_seconds=float(segment_seconds),
                    min_distance_m=float(segment_meta["min_distance_m"]),
                    min_duration_s=float(segment_meta["min_duration_s"]),
                    segment_dir=segment_dir,
                    args=args,
                )
            )

    best_by_energy_pct = min(rows, key=lambda row: row["flight_mean_abs_energy_error_pct"])
    best_by_range_p95 = min(rows, key=lambda row: row["range_p95_abs_error_pct"])
    payload = {
        "input": str(_resolve_path(args.input)),
        "route": args.route,
        "method": args.method,
        "targets": list(args.targets),
        "segment_seconds": [float(value) for value in args.segment_seconds],
        "group_col": args.group_col,
        "test_size": args.test_size,
        "battery_wh": args.battery_wh,
        "segment_views": segment_views,
        "results": rows,
        "best_by_flight_mean_abs_energy_error_pct": best_by_energy_pct,
        "best_by_range_p95_abs_error_pct": best_by_range_p95,
    }
    save_ablation_results(rows, output_dir / "comparison.csv")
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
