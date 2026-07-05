# 执行历史天气与机载风消融实验，比较不同天气信息组合对能耗预测的贡献。
"""执行历史天气与机载风消融实验。"""

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

from uav_energy_engine.dataset import build_training_dataset
from uav_energy_engine.evaluate import save_ablation_results, save_summary
from uav_energy_engine.model import train_energy_model


BASELINE_FEATURES = ["planned_ground_speed_mps", "payload_kg", "altitude_m"]
HISTORICAL_WEATHER_FEATURES = [
    "hist_wind_speed_mps",
    "hist_headwind_mps",
    "hist_crosswind_mps",
    "hist_wind_gust_mps",
    "hist_relative_humidity_pct",
    "hist_temperature_c",
    "hist_pressure_hpa",
    "hist_precipitation_mm",
    "hist_air_density_kgm3",
]
ONBOARD_WIND_FEATURES = ["wind_speed_mps", "headwind_mps", "crosswind_mps"]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="执行天气消融实验。")
    parser.add_argument(
        "--input",
        default="data/processed/flights_with_historical_weather.csv",
        help="带历史天气回填的统一飞行日志 CSV",
    )
    parser.add_argument("--route", default="R1", help="可选路线过滤")
    parser.add_argument("--output-dir", default="outputs/weather_ablation", help="实验输出目录")
    parser.add_argument(
        "--method",
        default="linear_residual_gb",
        help="单模型训练方法，默认使用线性基线加残差提升树",
    )
    parser.add_argument("--group-col", default="date", help="训练/测试切分使用的分组列")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    return parser.parse_args()


def variant_feature_map() -> dict:
    """返回三组消融实验的特征配置。"""

    return {
        "no_weather": BASELINE_FEATURES,
        "historical_weather": BASELINE_FEATURES + HISTORICAL_WEATHER_FEATURES,
        "historical_weather_plus_onboard_wind": BASELINE_FEATURES
        + HISTORICAL_WEATHER_FEATURES
        + ONBOARD_WIND_FEATURES,
    }


def main() -> None:
    """执行消融实验主流程。"""

    args = parse_args()
    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    features_csv = output_dir / "features.csv"
    build_training_dataset(
        input_csv=ROOT / args.input if not Path(args.input).is_absolute() else Path(args.input),
        output_csv=features_csv,
        route=args.route or None,
    )

    rows = []
    best_row = None
    for variant, feature_cols in variant_feature_map().items():
        variant_dir = output_dir / variant
        metrics = train_energy_model(
            features_csv=features_csv,
            model_out=variant_dir / "model.pkl",
            metrics_out=variant_dir / "metrics.json",
            random_state=args.random_state,
            method=args.method,
            target="energy_wh_per_km",
            feature_cols=feature_cols,
            base_cols=BASELINE_FEATURES,
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

    comparison_csv = output_dir / "comparison.csv"
    comparison_json = output_dir / "summary.json"
    save_ablation_results(rows, comparison_csv)
    payload = {
        "input_csv": str(features_csv.resolve()),
        "route": args.route,
        "method": args.method,
        "group_col": args.group_col,
        "test_size": args.test_size,
        "results": rows,
        "best_by_rmse": best_row,
    }
    save_summary(payload, comparison_json)
    print(json.dumps(payload["best_by_rmse"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
