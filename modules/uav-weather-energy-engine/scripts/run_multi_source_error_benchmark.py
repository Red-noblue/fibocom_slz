# 评估多来源训练表在源域和飞行阶段上的误差，并比较残差修正策略。
"""运行多来源能耗模型误差基准。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from uav_energy_engine.error_analysis import (
    build_flight_error_table,
    build_phase_error_table,
    build_segment_error_table_from_frame,
    summarize_error_tables,
)
from uav_energy_engine.evaluate import regression_metrics, save_ablation_results, save_summary
from uav_energy_engine.model import _fit_model, _prepare_training_frame
from uav_energy_engine.phase_residual import wrap_with_categorical_residual_corrections
from uav_energy_engine.source_expert import fit_source_expert_model
from uav_energy_engine.target_modes import infer_target_mode


CORE_FEATURES = [
    "planned_ground_speed_mps",
    "payload_kg",
    "altitude_m",
    "distance_m",
    "duration_s",
    "heading_deg",
]

WEATHER_FEATURES = [
    "wind_speed_mps",
    "wind_dir_deg",
    "headwind_mps",
    "crosswind_mps",
    "wind_gust_mps",
    "temperature_c",
    "pressure_hpa",
    "relative_humidity_pct",
    "air_density_kgm3",
]

PHASE_DYNAMIC_FEATURES = [
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

SOURCE_FEATURES = [
    "source_is_m100",
    "source_is_wemuav",
    "role_is_route_calibration",
    "role_is_wind_phase_power_auxiliary",
]

PHASE_LABELS = [
    "climb",
    "descent",
    "level",
    "turn",
    "hover_or_slow",
    "cruise",
]

PHASE_ONEHOT_FEATURES = [f"phase_is_{phase}" for phase in PHASE_LABELS]
SOURCE_PHASE_INTERACTION_FEATURES = [
    f"source_is_m100_x_phase_is_{phase}" for phase in PHASE_LABELS
] + [
    f"source_is_wemuav_x_phase_is_{phase}" for phase in PHASE_LABELS
]

PRUNED_MULTI_SOURCE_FEATURES = [
    "planned_ground_speed_mps",
    "payload_kg",
    "altitude_m",
    "distance_m",
    "duration_s",
    "heading_deg",
    "wind_speed_mps",
    "wind_dir_deg",
    "headwind_mps",
    "crosswind_mps",
    "wind_gust_mps",
    "temperature_c",
    "relative_humidity_pct",
    "air_density_kgm3",
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
    "horizontal_speed_p95_mps",
    "acceleration_abs_mean_mps2",
    "acceleration_abs_p95_mps2",
    "turn_rate_mean_deg_s",
    "source_is_m100",
    "source_is_wemuav",
    "role_is_route_calibration",
    "role_is_wind_phase_power_auxiliary",
]


FEATURE_VARIANTS = {
    "physical": CORE_FEATURES + WEATHER_FEATURES + PHASE_DYNAMIC_FEATURES,
    "physical_source_flags": CORE_FEATURES + WEATHER_FEATURES + PHASE_DYNAMIC_FEATURES + SOURCE_FEATURES,
    "physical_source_flags_pruned": PRUNED_MULTI_SOURCE_FEATURES,
    "physical_source_flags_phase_interactions": CORE_FEATURES
    + WEATHER_FEATURES
    + PHASE_DYNAMIC_FEATURES
    + SOURCE_FEATURES
    + PHASE_ONEHOT_FEATURES
    + SOURCE_PHASE_INTERACTION_FEATURES,
}

CORRECTION_VARIANTS = {
    "none": [],
    "phase": [["phase_label"]],
    "source": [["source_dataset"]],
    "source_then_phase": [["source_dataset"], ["phase_label"]],
    "source_phase_joint": [["source_dataset", "phase_label"]],
    "source_expert": [],
    "source_phase_expert": [],
    "source_expert_phase": [["phase_label"]],
}

SAMPLE_WEIGHT_POLICIES = [
    "none",
    "distance_duration",
    "m100_hover_boost",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="运行多来源能耗模型误差基准。")
    parser.add_argument(
        "--features",
        default="outputs/multi_source_training/combined_power_preflight_weather_complete.csv",
        help="多来源训练表 CSV",
    )
    parser.add_argument("--output-dir", default="outputs/multi_source_training/error_benchmark", help="输出目录")
    parser.add_argument("--target", default="mean_power_w", help="训练目标列")
    parser.add_argument("--method", default="gradient_boosting", help="训练方法")
    parser.add_argument("--group-col", default="flight", help="训练/测试分组列")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--battery-wh", type=float, default=130.0, help="风险评估使用的电池容量 Wh")
    parser.add_argument("--min-group-rows", type=int, default=5, help="残差修正中单组最小行数")
    parser.add_argument("--min-expert-rows", type=int, default=20, help="源域专家模型单源最小训练行数")
    parser.add_argument("--shrinkage-rows", type=float, default=20.0, help="残差修正向全局偏差收缩的强度")
    parser.add_argument(
        "--sample-weight-policy",
        default="none",
        choices=SAMPLE_WEIGHT_POLICIES,
        help="训练样本权重策略",
    )
    parser.add_argument(
        "--feature-variants",
        nargs="+",
        default=["physical", "physical_source_flags", "physical_source_flags_pruned"],
        choices=sorted(FEATURE_VARIANTS),
        help="要比较的特征组",
    )
    parser.add_argument(
        "--corrections",
        nargs="+",
        default=[
            "none",
            "phase",
            "source",
            "source_then_phase",
            "source_phase_joint",
            "source_expert",
            "source_expert_phase",
        ],
        choices=sorted(CORRECTION_VARIANTS),
        help="要比较的残差修正策略",
    )
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _safe_name(value: object) -> str:
    """转换为安全目录名。"""

    return str(value).replace("/", "_").replace(" ", "_").replace(":", "_")


def _variant_name(feature_variant: str, correction_name: str, sample_weight_policy: str = "none") -> str:
    """生成包含权重策略的实验变体名。"""

    base = f"{feature_variant}__{correction_name}"
    if sample_weight_policy == "none":
        return base
    return f"{base}__weight_{sample_weight_policy}"


def _with_auxiliary_strategy_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """补充专家模型和问题切片需要的派生分类列。"""

    out = frame.copy()
    if "source_dataset" in out.columns and "phase_label" in out.columns:
        phase_labels = out["phase_label"].fillna("unknown").astype(str)
        source_labels = out["source_dataset"].fillna("unknown").astype(str)
        out["source_phase_key"] = (
            source_labels + "|" + phase_labels
        )
        out["is_m100_hover_or_slow"] = (
            (source_labels == "m100") & (phase_labels == "hover_or_slow")
        ).astype(float)
        if "source_is_m100" not in out.columns:
            out["source_is_m100"] = (source_labels == "m100").astype(float)
        if "source_is_wemuav" not in out.columns:
            out["source_is_wemuav"] = (source_labels == "wemuav").astype(float)
        source_is_m100 = pd.to_numeric(out["source_is_m100"], errors="coerce").fillna(0.0)
        source_is_wemuav = pd.to_numeric(out["source_is_wemuav"], errors="coerce").fillna(0.0)
        for phase in PHASE_LABELS:
            phase_column = f"phase_is_{phase}"
            out[phase_column] = (phase_labels == phase).astype(float)
            out[f"source_is_m100_x_{phase_column}"] = source_is_m100 * out[phase_column]
            out[f"source_is_wemuav_x_{phase_column}"] = source_is_wemuav * out[phase_column]
    return out


def _normalise_weight_series(weights: pd.Series) -> pd.Series:
    """把权重归一到均值约为 1，避免改变目标量纲。"""

    cleaned = pd.to_numeric(weights, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(1.0)
    cleaned = cleaned.clip(lower=0.05)
    mean_value = float(cleaned.mean())
    if not np.isfinite(mean_value) or mean_value <= 1e-9:
        return pd.Series(1.0, index=weights.index, dtype=float)
    return cleaned / mean_value


def _compute_sample_weight(frame: pd.DataFrame, policy: str) -> Optional[pd.Series]:
    """根据分段可信度或问题切片生成训练样本权重。"""

    if policy == "none":
        return None

    weights = pd.Series(1.0, index=frame.index, dtype=float)
    if policy == "distance_duration":
        distance = pd.to_numeric(frame.get("distance_m", pd.Series(np.nan, index=frame.index)), errors="coerce")
        duration = pd.to_numeric(frame.get("duration_s", pd.Series(np.nan, index=frame.index)), errors="coerce")
        distance_ref = float(distance.dropna().median()) if distance.notna().any() else 1.0
        duration_ref = float(duration.dropna().median()) if duration.notna().any() else 1.0
        distance_ratio = (distance / max(distance_ref, 1e-6)).clip(lower=0.10, upper=4.0).fillna(1.0)
        duration_ratio = (duration / max(duration_ref, 1e-6)).clip(lower=0.25, upper=2.0).fillna(1.0)
        weights = np.sqrt(distance_ratio * duration_ratio).clip(lower=0.50, upper=2.0)
        return _normalise_weight_series(pd.Series(weights, index=frame.index, dtype=float))

    if policy == "m100_hover_boost":
        if {"source_dataset", "phase_label"}.issubset(frame.columns):
            mask = (
                (frame["source_dataset"].fillna("").astype(str) == "m100")
                & (frame["phase_label"].fillna("").astype(str) == "hover_or_slow")
            )
            weights.loc[mask] = 2.0
        return _normalise_weight_series(weights)

    raise ValueError(f"不支持的样本权重策略: {policy}")


def _feature_columns_for_variant(input_path: Path, target: str, frame: pd.DataFrame, feature_variant: str) -> list[str]:
    """解析一个特征组在当前训练表中实际可用的特征列。"""

    if feature_variant == "physical_source_flags_phase_interactions":
        return [column for column in FEATURE_VARIANTS[feature_variant] if column in frame.columns]

    _, feature_cols = _prepare_training_frame(input_path, [target], FEATURE_VARIANTS[feature_variant])
    return [column for column in feature_cols if column in frame.columns]


def _split_frame(
    frame: pd.DataFrame,
    group_col: Optional[str],
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """按飞行等分组切分训练集和测试集。"""

    if group_col and group_col in frame.columns and frame[group_col].nunique(dropna=False) >= 2:
        groups = frame[group_col].fillna("__nan__").astype(str)
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        train_idx, test_idx = next(splitter.split(frame, groups=groups))
        meta = {
            "split_strategy": "group",
            "group_col": group_col,
            "total_group_count": int(groups.nunique(dropna=False)),
            "train_group_count": int(groups.iloc[train_idx].nunique(dropna=False)),
            "test_group_count": int(groups.iloc[test_idx].nunique(dropna=False)),
        }
        return frame.iloc[train_idx].copy(), frame.iloc[test_idx].copy(), meta

    train_frame, test_frame = train_test_split(frame, test_size=test_size, random_state=random_state)
    return train_frame.copy(), test_frame.copy(), {"split_strategy": "random", "group_col": group_col}


def _source_error_table(segment_errors: pd.DataFrame) -> pd.DataFrame:
    """按数据源统计误差。"""

    if "source_dataset" not in segment_errors.columns:
        return pd.DataFrame()

    rows = []
    for source, group in segment_errors.groupby("source_dataset", sort=False):
        actual = pd.to_numeric(group["actual_target_value"], errors="coerce")
        predicted = pd.to_numeric(group["predicted_target_value"], errors="coerce")
        metrics = regression_metrics(actual.to_numpy(dtype=float), predicted.to_numpy(dtype=float))
        rows.append(
            {
                "source_dataset": source,
                "count": int(len(group.index)),
                "flight_count": int(group["flight"].nunique()) if "flight" in group.columns else None,
                "target_rmse": metrics["rmse"],
                "target_mae": metrics["mae"],
                "target_r2": metrics["r2"],
                "target_naive_rmse": metrics["naive_rmse"],
                "mean_abs_target_error_pct": float(pd.to_numeric(group["abs_target_error_pct"], errors="coerce").mean()),
                "mean_abs_segment_energy_error_wh": float(
                    pd.to_numeric(group["abs_segment_energy_error_wh"], errors="coerce").mean()
                ),
                "mean_abs_segment_energy_error_pct": float(
                    pd.to_numeric(group["abs_segment_energy_error_pct"], errors="coerce").mean()
                ),
                "actual_target_mean": float(actual.mean()),
                "predicted_target_mean": float(predicted.mean()),
            }
        )
    return pd.DataFrame(rows)


def _correction_meta(model) -> list[dict]:
    """提取残差修正参数摘要。"""

    corrections = getattr(model, "corrections", [])
    rows = []
    if hasattr(model, "expert_counts"):
        rows.append(
            {
                "expert_col": getattr(model, "expert_col", None),
                "expert_counts": dict(getattr(model, "expert_counts", {})),
                "experts": sorted(list(getattr(model, "experts", {}).keys())),
            }
        )
    for correction in corrections:
        rows.append(
            {
                "group_cols": list(correction.group_cols),
                "offsets": dict(correction.offsets),
                "counts": dict(correction.counts),
                "default_offset": float(correction.default_offset),
                "shrinkage_rows": float(correction.shrinkage_rows),
            }
        )
    return rows


def _summary_row(
    variant: str,
    feature_variant: str,
    correction_name: str,
    sample_weight_policy: str,
    sample_weight: Optional[pd.Series],
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    feature_cols: list[str],
    segment_errors: pd.DataFrame,
    summary: dict,
) -> dict:
    """压平一个实验变体的摘要。"""

    segment = summary["segment"]
    flight = summary["flight"]
    risk = summary.get("risk", {})
    source_metrics = _source_error_table(segment_errors)
    mean_abs_segment_energy_error_wh = float(
        pd.to_numeric(segment_errors["abs_segment_energy_error_wh"], errors="coerce").mean()
    )
    mean_abs_segment_energy_error_pct = float(
        pd.to_numeric(segment_errors["abs_segment_energy_error_pct"], errors="coerce").mean()
    )
    row = {
        "variant": variant,
        "feature_variant": feature_variant,
        "correction": correction_name,
        "sample_weight_policy": sample_weight_policy,
        "target": segment.get("target"),
        "target_mode": segment.get("target_mode"),
        "feature_count": len(feature_cols),
        "train_count": int(len(train_frame.index)),
        "test_count": int(len(test_frame.index)),
        "train_flight_count": int(train_frame["flight"].nunique()) if "flight" in train_frame.columns else None,
        "test_flight_count": int(test_frame["flight"].nunique()) if "flight" in test_frame.columns else None,
        "segment_rmse": segment.get("rmse"),
        "segment_mae": segment.get("mae"),
        "segment_r2": segment.get("r2"),
        "segment_naive_rmse": segment.get("naive_rmse"),
        "segment_mean_abs_target_error_pct": segment.get("mean_abs_target_error_pct"),
        "segment_mean_abs_energy_error_wh": mean_abs_segment_energy_error_wh,
        "segment_mean_abs_energy_error_pct": mean_abs_segment_energy_error_pct,
        "flight_mean_abs_energy_error_wh": flight.get("mean_abs_energy_error_wh"),
        "flight_mean_abs_energy_error_pct": flight.get("mean_abs_energy_error_pct"),
        "range_mean_abs_error_pct": flight.get("mean_abs_range_error_pct"),
        "range_overprediction_gt_25pct_count": risk.get("range_overprediction_gt_25pct_count"),
        "energy_underprediction_gt_25pct_count": risk.get("energy_underprediction_gt_25pct_count"),
    }
    if sample_weight is not None:
        weights = pd.to_numeric(sample_weight, errors="coerce")
        row.update(
            {
                "sample_weight_mean": float(weights.mean()),
                "sample_weight_min": float(weights.min()),
                "sample_weight_max": float(weights.max()),
            }
        )
    for _, source_row in source_metrics.iterrows():
        prefix = f"source_{_safe_name(source_row['source_dataset'])}"
        row[f"{prefix}_count"] = int(source_row["count"])
        row[f"{prefix}_target_rmse"] = source_row["target_rmse"]
        row[f"{prefix}_target_mae"] = source_row["target_mae"]
        row[f"{prefix}_mean_abs_energy_pct"] = source_row["mean_abs_segment_energy_error_pct"]
    return row


def _run_variant(
    cleaned: pd.DataFrame,
    feature_cols: list[str],
    feature_variant: str,
    correction_name: str,
    args: argparse.Namespace,
    output_dir: Path,
    split_meta: dict,
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
) -> dict:
    """训练并评估一个实验变体。"""

    sample_weight_policy = getattr(args, "sample_weight_policy", "none")
    variant = _variant_name(feature_variant, correction_name, sample_weight_policy)
    variant_dir = output_dir / _safe_name(variant)
    variant_dir.mkdir(parents=True, exist_ok=True)
    train_frame = _with_auxiliary_strategy_columns(train_frame)
    test_frame = _with_auxiliary_strategy_columns(test_frame)
    sample_weight = _compute_sample_weight(train_frame, sample_weight_policy)
    x_train = train_frame[feature_cols].copy()
    y_train = pd.to_numeric(train_frame[args.target], errors="coerce")
    base_cols = [column for column in CORE_FEATURES if column in feature_cols]
    if correction_name == "source_phase_expert":
        model = fit_source_expert_model(
            train_frame=train_frame,
            target=args.target,
            feature_cols=feature_cols,
            method=args.method,
            random_state=args.random_state,
            expert_col="source_phase_key",
            min_expert_rows=args.min_expert_rows,
            base_cols=base_cols,
            sample_weight=sample_weight,
        )
    elif correction_name.startswith("source_expert"):
        model = fit_source_expert_model(
            train_frame=train_frame,
            target=args.target,
            feature_cols=feature_cols,
            method=args.method,
            random_state=args.random_state,
            expert_col="source_dataset",
            min_expert_rows=args.min_expert_rows,
            base_cols=base_cols,
            sample_weight=sample_weight,
        )
    else:
        model = _fit_model(
            x_train=x_train,
            y_train=y_train,
            feature_cols=feature_cols,
            method=args.method,
            random_state=args.random_state,
            base_cols=base_cols,
            sample_weight=sample_weight,
        )
    correction_groups = [
        group_cols
        for group_cols in CORRECTION_VARIANTS[correction_name]
        if set(group_cols).issubset(train_frame.columns)
    ]
    if correction_groups:
        model = wrap_with_categorical_residual_corrections(
            base_model=model,
            train_frame=train_frame,
            target=args.target,
            correction_groups=correction_groups,
            min_group_rows=args.min_group_rows,
            shrinkage_rows=args.shrinkage_rows,
        )

    segment_errors, segment_meta = build_segment_error_table_from_frame(
        model=model,
        test_frame=test_frame,
        target=args.target,
        segment_meta={
            **split_meta,
            "feature_variant": feature_variant,
            "correction": correction_name,
            "sample_weight_policy": sample_weight_policy,
            "correction_meta": _correction_meta(model),
        },
    )
    flight_errors = build_flight_error_table(segment_errors, battery_wh=args.battery_wh, group_col="flight")
    summary = summarize_error_tables(
        segment_errors=segment_errors,
        flight_errors=flight_errors,
        segment_meta=segment_meta,
        battery_wh=args.battery_wh,
    )
    source_errors = _source_error_table(segment_errors)
    phase_errors = build_phase_error_table(segment_errors) if "phase_label" in segment_errors.columns else pd.DataFrame()

    segment_errors.to_csv(variant_dir / "segment_errors.csv", index=False)
    flight_errors.to_csv(variant_dir / "flight_errors.csv", index=False)
    source_errors.to_csv(variant_dir / "source_errors.csv", index=False)
    if not phase_errors.empty:
        phase_errors.to_csv(variant_dir / "phase_errors.csv", index=False)
    save_summary(
        {
            "variant": variant,
            "feature_variant": feature_variant,
            "correction": correction_name,
            "sample_weight_policy": sample_weight_policy,
            "features": feature_cols,
            "summary": summary,
            "source_errors": source_errors.to_dict(orient="records"),
            "correction_meta": _correction_meta(model),
        },
        variant_dir / "summary.json",
    )
    return _summary_row(
        variant=variant,
        feature_variant=feature_variant,
        correction_name=correction_name,
        sample_weight_policy=sample_weight_policy,
        sample_weight=sample_weight,
        train_frame=train_frame,
        test_frame=test_frame,
        feature_cols=feature_cols,
        segment_errors=segment_errors,
        summary=summary,
    )


def main() -> None:
    """执行多来源误差基准。"""

    args = parse_args()
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = _resolve_path(args.features)

    all_requested_features = sorted(
        {
            feature
            for feature_variant in args.feature_variants
            for feature in FEATURE_VARIANTS[feature_variant]
        }
    )
    cleaned, _ = _prepare_training_frame(input_path, [args.target], all_requested_features)
    cleaned = _with_auxiliary_strategy_columns(cleaned)
    train_frame, test_frame, split_meta = _split_frame(
        frame=cleaned,
        group_col=args.group_col,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    train_frame.to_csv(output_dir / "train_frame.csv", index=False)
    test_frame.to_csv(output_dir / "test_frame.csv", index=False)

    rows = []
    for feature_variant in args.feature_variants:
        feature_cols = _feature_columns_for_variant(input_path, args.target, cleaned, feature_variant)
        train_subset = train_frame.dropna(subset=feature_cols + [args.target]).copy()
        test_subset = test_frame.dropna(subset=feature_cols + [args.target]).copy()
        if train_subset.empty or test_subset.empty:
            continue
        for correction_name in args.corrections:
            rows.append(
                _run_variant(
                    cleaned=cleaned,
                    feature_cols=feature_cols,
                    feature_variant=feature_variant,
                    correction_name=correction_name,
                    args=args,
                    output_dir=output_dir,
                    split_meta=split_meta,
                    train_frame=train_subset,
                    test_frame=test_subset,
                )
            )

    comparison = save_ablation_results(rows, output_dir / "comparison.csv")
    best_by_segment = comparison.sort_values("segment_rmse").iloc[0].to_dict() if not comparison.empty else None
    best_by_energy_pct = (
        comparison.sort_values("segment_mean_abs_energy_error_pct").iloc[0].to_dict()
        if not comparison.empty
        else None
    )
    payload = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "target": args.target,
        "target_mode": infer_target_mode(args.target),
        "method": args.method,
        "split": split_meta,
        "row_counts": {
            "cleaned": int(len(cleaned.index)),
            "train": int(len(train_frame.index)),
            "test": int(len(test_frame.index)),
            "comparison_rows": int(len(comparison.index)),
        },
        "feature_variants": args.feature_variants,
        "corrections": args.corrections,
        "sample_weight_policy": args.sample_weight_policy,
        "best_by_segment_rmse": best_by_segment,
        "best_by_segment_mean_abs_energy_error_pct": best_by_energy_pct,
        "outputs": {
            "comparison": str((output_dir / "comparison.csv").resolve()),
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
