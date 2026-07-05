# 固化当前默认部署候选策略，输出可训练、可评估、可复用的模型产物。
"""训练正式部署模型。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd

from run_mass_assumption_experiment import (
    DEFAULT_ASSUMED_EMPTY_MASS_KG,
    add_phase_onehot,
    apply_mass_assumption,
    assert_no_source_features,
    audit_mass_source_proxy_risk,
    compute_sample_weight,
    ensure_payload_kg,
    feature_columns_for_assumption,
    split_frame,
    _clean_for_training,
)
from uav_energy_engine.altitude_profiles import apply_altitude_profile
from uav_energy_engine.error_analysis import (
    build_flight_error_table,
    build_phase_error_table,
    build_segment_error_table_from_frame,
    summarize_error_tables,
)
from uav_energy_engine.evaluate import save_summary
from uav_energy_engine.model import _fit_model, save_model_object
from uav_energy_engine.phase_residual import wrap_with_categorical_residual_corrections
from uav_energy_engine.planned_equivalent_features import add_planned_equivalent_wind_features
from uav_energy_engine.wind_profiles import apply_wind_profile


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="训练当前默认部署候选模型。")
    parser.add_argument(
        "--features",
        default="outputs/multi_source_training/combined_power_preflight_weather_complete.csv",
        help="多来源训练表 CSV",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/deployment_model_default",
        help="训练输出目录",
    )
    parser.add_argument("--target", default="mean_power_w", help="训练目标列")
    parser.add_argument("--method", default="gradient_boosting", help="基础训练方法")
    parser.add_argument("--group-col", default="flight", help="训练/测试分组列")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--battery-wh", type=float, default=130.0, help="风险评估使用的电池容量 Wh")
    parser.add_argument("--sample-weight-policy", default="phase_balanced", help="训练样本权重策略")
    parser.add_argument("--wind-profile", default="height_weather", help="风字段口径")
    parser.add_argument("--altitude-profile", default="planned_level", help="高度字段口径")
    parser.add_argument("--mass-assumption", default="payload_only", help="质量字段假设")
    parser.add_argument("--correction", default="phase", choices=["none", "phase"], help="默认部署修正策略")
    parser.add_argument("--min-group-rows", type=int, default=5, help="阶段残差修正中单阶段最小行数")
    parser.add_argument("--shrinkage-rows", type=float, default=20.0, help="阶段残差收缩强度")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    """执行默认部署模型训练。"""

    args = parse_args()
    input_path = _resolve_path(args.features)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(input_path)
    frame, wind_profile_meta = apply_wind_profile(frame, args.wind_profile)
    frame, altitude_profile_meta = apply_altitude_profile(frame, args.altitude_profile)
    frame = add_phase_onehot(add_planned_equivalent_wind_features(ensure_payload_kg(frame)))
    train_frame, test_frame, split_meta = split_frame(
        frame=frame,
        group_col=args.group_col,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    train_mass, mass_feature_cols, mass_meta = apply_mass_assumption(
        train_frame,
        assumption=args.mass_assumption,
        assumed_empty_mass_by_source=DEFAULT_ASSUMED_EMPTY_MASS_KG,
    )
    test_mass, _, _ = apply_mass_assumption(
        test_frame,
        assumption=args.mass_assumption,
        assumed_empty_mass_by_source=DEFAULT_ASSUMED_EMPTY_MASS_KG,
    )
    mass_meta.update(audit_mass_source_proxy_risk(train_mass, mass_feature_cols))

    feature_cols = feature_columns_for_assumption(
        train_mass,
        mass_feature_cols,
        exclude_features=[],
        equivalent_wind_feature_set="none",
    )
    assert_no_source_features(feature_cols)

    train_clean = _clean_for_training(train_mass, feature_cols, args.target)
    test_clean = _clean_for_training(test_mass, feature_cols, args.target)
    sample_weight = compute_sample_weight(train_clean, args.sample_weight_policy)
    base_cols = [
        column
        for column in ["planned_ground_speed_mps", "payload_kg", "altitude_m"]
        if column in feature_cols
    ]
    model = _fit_model(
        x_train=train_clean[list(feature_cols)].copy(),
        y_train=pd.to_numeric(train_clean[args.target], errors="coerce"),
        feature_cols=feature_cols,
        method=args.method,
        random_state=args.random_state,
        base_cols=base_cols,
        sample_weight=sample_weight,
    )
    if args.correction == "phase":
        model = wrap_with_categorical_residual_corrections(
            base_model=model,
            train_frame=train_clean,
            target=args.target,
            correction_groups=[["phase_label"]],
            min_group_rows=args.min_group_rows,
            shrinkage_rows=args.shrinkage_rows,
        )

    model_path = output_dir / "model.pkl"
    save_model_object(model, model_path)

    segment_errors, segment_meta = build_segment_error_table_from_frame(
        model=model,
        test_frame=test_clean,
        target=args.target,
        segment_meta={
            **split_meta,
            "target": args.target,
            "features": list(feature_cols),
            "mass_assumption": args.mass_assumption,
            "correction": args.correction,
            "sample_weight_policy": args.sample_weight_policy,
            "wind_profile": args.wind_profile,
            "altitude_profile": args.altitude_profile,
            "equivalent_wind_feature_set": "none",
            "uses_source_dataset_as_feature": False,
            "mass_meta": mass_meta,
            "model_path": str(model_path.resolve()),
        },
    )
    flight_errors = build_flight_error_table(segment_errors, battery_wh=args.battery_wh, group_col="flight")
    phase_errors = build_phase_error_table(segment_errors) if "phase_label" in segment_errors.columns else pd.DataFrame()
    summary = summarize_error_tables(segment_errors, flight_errors, segment_meta, battery_wh=args.battery_wh)

    train_clean.to_csv(output_dir / "train_frame.csv", index=False)
    test_clean.to_csv(output_dir / "test_frame.csv", index=False)
    segment_errors.to_csv(output_dir / "segment_errors.csv", index=False)
    flight_errors.to_csv(output_dir / "flight_errors.csv", index=False)
    if not phase_errors.empty:
        phase_errors.to_csv(output_dir / "phase_errors.csv", index=False)

    payload = {
        "input": str(input_path.resolve()),
        "output_dir": str(output_dir.resolve()),
        "model_path": str(model_path.resolve()),
        "target": args.target,
        "method": args.method,
        "mass_assumption": args.mass_assumption,
        "correction": args.correction,
        "sample_weight_policy": args.sample_weight_policy,
        "wind_profile": args.wind_profile,
        "wind_profile_meta": wind_profile_meta,
        "altitude_profile": args.altitude_profile,
        "altitude_profile_meta": altitude_profile_meta,
        "equivalent_wind_feature_set": "none",
        "feature_count": int(len(feature_cols)),
        "features": list(feature_cols),
        "mass_meta": mass_meta,
        "split": split_meta,
        "row_counts": {
            "input": int(len(frame.index)),
            "train": int(len(train_clean.index)),
            "test": int(len(test_clean.index)),
        },
        "sample_weight_stats": None
        if sample_weight is None
        else {
            "mean": float(pd.to_numeric(sample_weight, errors="coerce").mean()),
            "min": float(pd.to_numeric(sample_weight, errors="coerce").min()),
            "max": float(pd.to_numeric(sample_weight, errors="coerce").max()),
        },
        "summary": summary,
        "outputs": {
            "train_frame": str((output_dir / "train_frame.csv").resolve()),
            "test_frame": str((output_dir / "test_frame.csv").resolve()),
            "segment_errors": str((output_dir / "segment_errors.csv").resolve()),
            "flight_errors": str((output_dir / "flight_errors.csv").resolve()),
            "phase_errors": str((output_dir / "phase_errors.csv").resolve()) if not phase_errors.empty else None,
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
