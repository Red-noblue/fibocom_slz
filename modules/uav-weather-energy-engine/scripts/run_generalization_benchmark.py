# 评估能耗模型在未见飞行、路线、日期、航速和高度上的泛化能力。
"""运行真实飞行泛化能力基准实验。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


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
    build_segment_error_table_from_frame,
    summarize_error_tables,
)
from uav_energy_engine.evaluate import regression_metrics, save_ablation_results, save_summary
from uav_energy_engine.model import _fit_model, _prepare_training_frame
from uav_energy_engine.phase_residual import wrap_with_phase_residual_correction
from uav_energy_engine.route_features import ROUTE_GEOMETRY_FEATURE_COLUMNS, build_preflight_training_feature_view
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

ROUTE_GEOMETRY_FEATURES = list(ROUTE_GEOMETRY_FEATURE_COLUMNS)

DEFAULT_SPLITS = [
    "flight_shuffle",
    "route_holdout",
    "date_holdout",
    "speed_holdout",
    "altitude_holdout",
]

FEATURE_PRESETS = [
    "validated",
    "validated_pruned",
    "all",
    "core",
    "core_weather",
    "core_route",
    "core_phase",
    "core_weather_route",
    "core_weather_phase",
    "core_route_phase",
    "all_no_weather",
    "all_no_route",
    "all_no_phase",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="评估能耗模型在不同未见分布上的泛化能力。")
    parser.add_argument("--input", default="data/processed/flights_with_historical_weather_100m.csv", help="输入飞行日志 CSV")
    parser.add_argument("--output-dir", default="outputs/generalization_benchmark", help="实验输出目录")
    parser.add_argument("--route", default=None, help="可选路线过滤；默认不过滤，便于跨路线验证")
    parser.add_argument("--segment-seconds", type=float, default=120.0, help="分段长度，单位秒")
    parser.add_argument("--target", default="segment_wh_per_s", help="预测目标列")
    parser.add_argument("--splits", nargs="+", default=DEFAULT_SPLITS, help="要运行的泛化切分")
    parser.add_argument("--min-distance-m", type=float, default=None, help="固定最小分段距离；不填则按分段秒数推断")
    parser.add_argument("--min-duration-s", type=float, default=None, help="固定最小分段时长；不填则按分段秒数推断")
    parser.add_argument("--min-distance-mps", type=float, default=0.833333, help="自动最小分段距离系数，单位 m/s")
    parser.add_argument("--min-duration-ratio", type=float, default=0.25, help="自动最小分段时长占分段秒数的比例")
    parser.add_argument("--target-min", type=float, default=None, help="可选：按每公里能耗过滤异常分段的下限")
    parser.add_argument("--target-max", type=float, default=None, help="可选：按每公里能耗过滤异常分段的上限")
    parser.add_argument("--method", default="gradient_boosting", help="训练方法")
    parser.add_argument(
        "--feature-preset",
        default="validated_pruned",
        choices=FEATURE_PRESETS,
        help="特征预设；validated_pruned 为当前验证后的默认最优子集",
    )
    parser.add_argument("--test-size", type=float, default=0.2, help="随机飞行留出比例")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--battery-wh", type=float, default=130.0, help="可达性风险评估使用的电池容量 Wh")
    parser.add_argument("--min-train-rows", type=int, default=20, help="单个泛化折的最小训练行数")
    parser.add_argument("--min-test-rows", type=int, default=3, help="单个泛化折的最小测试行数")
    parser.add_argument("--max-numeric-groups", type=int, default=8, help="数值分组唯一值过多时的最大分箱数")
    parser.add_argument("--phase-residual-correction", action="store_true", help="启用飞行阶段残差修正")
    parser.add_argument("--phase-column", default="phase_label", help="阶段残差修正使用的阶段列")
    parser.add_argument("--phase-min-rows", type=int, default=5, help="单个阶段至少多少训练行才学习独立修正")
    parser.add_argument("--phase-shrinkage-rows", type=float, default=20.0, help="阶段残差向全局残差收缩的强度")
    parser.add_argument("--save-fold-models", action="store_true", help="保存每个泛化折的模型文件")
    return parser.parse_args()


def _requested_features_for_preset(preset: str) -> list[str]:
    """根据预设返回训练特征列表。"""

    if preset == "validated":
        preset = "core_route_phase"
    if preset == "validated_pruned":
        return [
            "planned_ground_speed_mps",
            "payload_kg",
            "altitude_m",
            "distance_m",
            "heading_deg",
            "heading_cos",
            "route_direct_distance_m",
            "route_total_distance_m",
            "route_segment_count",
            "route_remaining_distance_m",
            "route_turn_density_deg_per_km",
            "segment_turn_density_deg_per_km",
            "route_bearing_sin",
            "route_bearing_cos",
            "segment_route_cross_alignment",
            "route_total_altitude_loss_m",
            "route_altitude_range_m",
            "route_descent_density_m_per_km",
            "climb_ratio",
            "turn_ratio",
            "hover_or_slow_ratio",
            "altitude_range_m",
            "altitude_gain_m",
            "vertical_speed_abs_mean_mps",
            "horizontal_speed_std_mps",
            "horizontal_speed_p95_mps",
            "acceleration_abs_mean_mps2",
            "acceleration_abs_p95_mps2",
            "turn_rate_p95_deg_s",
        ]
    if preset == "all":
        return CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES + ROUTE_GEOMETRY_FEATURES + PHASE_AND_DYNAMIC_FEATURES
    if preset == "core":
        return list(CORE_FLIGHT_FEATURES)
    if preset == "core_weather":
        return CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES
    if preset == "core_route":
        return CORE_FLIGHT_FEATURES + ROUTE_GEOMETRY_FEATURES
    if preset == "core_phase":
        return CORE_FLIGHT_FEATURES + PHASE_AND_DYNAMIC_FEATURES
    if preset == "core_weather_route":
        return CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES + ROUTE_GEOMETRY_FEATURES
    if preset == "core_weather_phase":
        return CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES + PHASE_AND_DYNAMIC_FEATURES
    if preset == "core_route_phase" or preset == "all_no_weather":
        return CORE_FLIGHT_FEATURES + ROUTE_GEOMETRY_FEATURES + PHASE_AND_DYNAMIC_FEATURES
    if preset == "all_no_route":
        return CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES + PHASE_AND_DYNAMIC_FEATURES
    if preset == "all_no_phase":
        return CORE_FLIGHT_FEATURES + PREFLIGHT_WEATHER_FEATURES + ROUTE_GEOMETRY_FEATURES
    raise ValueError(f"不支持的特征预设: {preset}")


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _safe_name(value: object) -> str:
    """把参数值转换为安全目录名。"""

    return str(value).replace("/", "_").replace(".", "p").replace(" ", "_").replace(":", "_")


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


def _prepare_feature_view(args: argparse.Namespace, output_dir: Path) -> tuple[Path, dict]:
    """构建泛化实验使用的部署口径特征表。"""

    min_distance_m = _auto_min_distance_m(args.segment_seconds, args)
    min_duration_s = _auto_min_duration_s(args.segment_seconds, args)
    onboard_csv = output_dir / "segment_features_onboard.csv"
    onboard_frame = build_segment_dataset(
        input_csv=_resolve_path(args.input),
        output_csv=onboard_csv,
        route=args.route or None,
        segment_seconds=args.segment_seconds,
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

    preflight_csv = output_dir / "segment_features_preflight.csv"
    preflight_frame = build_preflight_training_feature_view(onboard_frame)
    preflight_frame = _add_derived_targets(preflight_frame)
    preflight_frame.to_csv(preflight_csv, index=False)
    meta = {
        "segment_seconds": float(args.segment_seconds),
        "min_distance_m": float(min_distance_m),
        "min_duration_s": float(min_duration_s),
        "route_filter": args.route,
        "filter": filter_meta,
        "onboard_csv": str(onboard_csv.resolve()),
        "preflight_csv": str(preflight_csv.resolve()),
        "row_count": int(len(preflight_frame.index)),
        "flight_count": int(preflight_frame["flight"].nunique()) if "flight" in preflight_frame.columns else None,
        "route_count": int(preflight_frame["route"].nunique()) if "route" in preflight_frame.columns else None,
        "date_count": int(preflight_frame["date"].nunique()) if "date" in preflight_frame.columns else None,
    }
    return preflight_csv, meta


def _numeric_group_series(frame: pd.DataFrame, column: str, max_groups: int) -> pd.Series:
    """把数值列转换为泛化验证分组。"""

    values = pd.to_numeric(frame[column], errors="coerce")
    unique_values = sorted(values.dropna().unique().tolist())
    if len(unique_values) <= max_groups:
        return values.map(lambda value: f"{column}_{value:g}" if pd.notna(value) else "__nan__")

    bins = min(max_groups, len(unique_values))
    bucket = pd.qcut(values, q=bins, duplicates="drop")
    return bucket.astype(str).fillna("__nan__")


def _make_group_series(frame: pd.DataFrame, split_name: str, max_numeric_groups: int) -> Optional[pd.Series]:
    """根据切分名称生成分组序列。"""

    if split_name == "route_holdout":
        return frame["route"].fillna("__nan__").astype(str) if "route" in frame.columns else None
    if split_name == "date_holdout":
        return frame["date"].fillna("__nan__").astype(str) if "date" in frame.columns else None
    if split_name == "speed_holdout":
        speed_col = "planned_ground_speed_mps" if "planned_ground_speed_mps" in frame.columns else "speed_mps"
        return _numeric_group_series(frame, speed_col, max_numeric_groups) if speed_col in frame.columns else None
    if split_name == "altitude_holdout":
        return _numeric_group_series(frame, "altitude_m", max_numeric_groups) if "altitude_m" in frame.columns else None
    if split_name == "flight_shuffle":
        return frame["flight"].fillna("__nan__").astype(str) if "flight" in frame.columns else None
    raise ValueError(f"不支持的泛化切分: {split_name}")


def _iter_split_masks(
    frame: pd.DataFrame,
    split_name: str,
    groups: pd.Series,
    args: argparse.Namespace,
):
    """生成训练/测试掩码。"""

    if groups.nunique(dropna=False) < 2:
        return

    if split_name == "flight_shuffle":
        splitter = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=args.random_state)
        x_dummy = frame[["distance_m"]].copy() if "distance_m" in frame.columns else frame.iloc[:, :1].copy()
        train_idx, test_idx = next(splitter.split(x_dummy, frame[args.target], groups=groups))
        train_mask = pd.Series(False, index=frame.index)
        test_mask = pd.Series(False, index=frame.index)
        train_mask.iloc[train_idx] = True
        test_mask.iloc[test_idx] = True
        yield "shuffle", "flight_random_holdout", train_mask, test_mask
        return

    for group_value in sorted(groups.dropna().unique().tolist(), key=str):
        test_mask = groups == group_value
        train_mask = ~test_mask
        yield _safe_name(group_value), group_value, train_mask, test_mask


def _train_and_score_fold(
    cleaned: pd.DataFrame,
    feature_cols: list[str],
    split_name: str,
    fold_name: str,
    holdout_group: object,
    train_mask: pd.Series,
    test_mask: pd.Series,
    args: argparse.Namespace,
    split_dir: Path,
) -> tuple[Optional[pd.DataFrame], Optional[dict]]:
    """训练并评估一个泛化折。"""

    train_frame = cleaned.loc[train_mask].copy()
    test_frame = cleaned.loc[test_mask].copy()
    if len(train_frame.index) < args.min_train_rows or len(test_frame.index) < args.min_test_rows:
        return None, {
            "split_strategy": split_name,
            "fold": fold_name,
            "holdout_group": str(holdout_group),
            "status": "skipped_too_few_rows",
            "skip_reason": "训练集或测试集行数低于阈值",
            "target": args.target,
            "target_mode": infer_target_mode(args.target),
            "train_count": int(len(train_frame.index)),
            "test_count": int(len(test_frame.index)),
        }

    x_train = train_frame[feature_cols].copy()
    y_train = pd.to_numeric(train_frame[args.target], errors="coerce")
    model = _fit_model(
        x_train=x_train,
        y_train=y_train,
        feature_cols=feature_cols,
        method=args.method,
        random_state=args.random_state,
        base_cols=[column for column in CORE_FLIGHT_FEATURES if column in feature_cols],
    )
    phase_residual_meta = None
    if args.phase_residual_correction:
        model = wrap_with_phase_residual_correction(
            base_model=model,
            train_frame=train_frame,
            target=args.target,
            phase_col=args.phase_column,
            min_phase_rows=args.phase_min_rows,
            shrinkage_rows=args.phase_shrinkage_rows,
        )
        correction = model.correction
        phase_residual_meta = {
            "phase_column": correction.phase_col,
            "phase_offsets": correction.offsets,
            "phase_counts": correction.counts,
            "phase_default_offset": correction.default_offset,
            "phase_shrinkage_rows": correction.shrinkage_rows,
        }

    fold_dir = split_dir / _safe_name(fold_name)
    fold_dir.mkdir(parents=True, exist_ok=True)
    model_path = None
    if args.save_fold_models:
        model_path = fold_dir / "model.pkl"
        model.save(model_path)

    segment_errors, segment_meta = build_segment_error_table_from_frame(
        model=model,
        test_frame=test_frame,
        target=args.target,
        segment_meta={
            "split_strategy": split_name,
            "fold": fold_name,
            "holdout_group": str(holdout_group),
            "phase_residual": phase_residual_meta,
        },
    )
    segment_errors["_split_strategy"] = split_name
    segment_errors["_fold"] = fold_name
    segment_errors["_holdout_group"] = str(holdout_group)
    flight_errors = build_flight_error_table(segment_errors, battery_wh=args.battery_wh, group_col="flight")
    summary = summarize_error_tables(
        segment_errors=segment_errors,
        flight_errors=flight_errors,
        segment_meta=segment_meta,
        battery_wh=args.battery_wh,
    )
    row = _summary_to_row(
        split_name=split_name,
        fold=fold_name,
        holdout_group=holdout_group,
        summary=summary,
        train_frame=train_frame,
        test_frame=test_frame,
        model_path=model_path,
    )
    row["status"] = "ok"
    if phase_residual_meta is not None:
        row["phase_residual_enabled"] = True
        row["phase_residual_offsets"] = json.dumps(phase_residual_meta["phase_offsets"], ensure_ascii=False)
    else:
        row["phase_residual_enabled"] = False
    return segment_errors, row


def _summary_to_row(
    split_name: str,
    fold: str,
    holdout_group: object,
    summary: dict,
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    model_path: Optional[Path] = None,
) -> dict:
    """把汇总结果压平成表格行。"""

    segment = summary["segment"]
    flight = summary["flight"]
    risk = summary.get("risk", {})
    return {
        "split_strategy": split_name,
        "fold": fold,
        "holdout_group": str(holdout_group),
        "target": segment.get("target"),
        "target_mode": segment.get("target_mode"),
        "train_count": int(len(train_frame.index)),
        "test_count": int(len(test_frame.index)),
        "train_flight_count": int(train_frame["flight"].nunique()) if "flight" in train_frame.columns else None,
        "test_flight_count": int(test_frame["flight"].nunique()) if "flight" in test_frame.columns else None,
        "test_route_count": int(test_frame["route"].nunique()) if "route" in test_frame.columns else None,
        "test_date_count": int(test_frame["date"].nunique()) if "date" in test_frame.columns else None,
        "segment_rmse": segment.get("rmse"),
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
        "model_path": str(model_path.resolve()) if model_path else None,
    }


def _combined_summary_row(
    split_name: str,
    segment_errors: pd.DataFrame,
    args: argparse.Namespace,
) -> tuple[dict, pd.DataFrame, dict]:
    """汇总一个切分策略的所有测试折。"""

    flight_errors = build_flight_error_table(segment_errors, battery_wh=args.battery_wh, group_col="flight")
    actual = pd.to_numeric(segment_errors["actual_target_value"], errors="coerce")
    predicted = pd.to_numeric(segment_errors["predicted_target_value"], errors="coerce")
    segment_meta = {
        "target": args.target,
        "target_mode": infer_target_mode(args.target),
        "features": [],
        "segment_metrics": regression_metrics(actual, predicted),
        "split_strategy": split_name,
        "rows_evaluated": int(len(segment_errors.index)),
    }
    summary = summarize_error_tables(
        segment_errors=segment_errors,
        flight_errors=flight_errors,
        segment_meta=segment_meta,
        battery_wh=args.battery_wh,
    )
    row = _summary_to_row(
        split_name=split_name,
        fold="combined",
        holdout_group="all_holdouts",
        summary=summary,
        train_frame=pd.DataFrame(index=[]),
        test_frame=segment_errors,
    )
    row["train_count"] = None
    row["train_flight_count"] = None
    row["combined_train_note"] = "多折汇总行没有唯一训练集；训练规模请查看 fold_metrics.csv"
    row["fold_count"] = int(segment_errors["_fold"].nunique()) if "_fold" in segment_errors.columns else 1
    row["status"] = "ok"
    return row, flight_errors, summary


def _run_one_split(
    split_name: str,
    cleaned: pd.DataFrame,
    feature_cols: list[str],
    args: argparse.Namespace,
    output_dir: Path,
) -> tuple[Optional[dict], list[dict]]:
    """运行一种泛化切分策略。"""

    groups = _make_group_series(cleaned, split_name, args.max_numeric_groups)
    split_dir = output_dir / split_name
    split_dir.mkdir(parents=True, exist_ok=True)
    if groups is None or groups.nunique(dropna=False) < 2:
        skipped = {
            "split_strategy": split_name,
            "fold": None,
            "holdout_group": None,
            "status": "skipped_group_unavailable",
            "skip_reason": "缺少可用分组列或分组数量不足",
            "target": args.target,
            "target_mode": infer_target_mode(args.target),
            "train_count": None,
            "test_count": None,
        }
        return None, [skipped]

    fold_rows = []
    all_segment_errors = []
    for fold_name, holdout_group, train_mask, test_mask in _iter_split_masks(cleaned, split_name, groups, args):
        segment_errors, row = _train_and_score_fold(
            cleaned=cleaned,
            feature_cols=feature_cols,
            split_name=split_name,
            fold_name=fold_name,
            holdout_group=holdout_group,
            train_mask=train_mask,
            test_mask=test_mask,
            args=args,
            split_dir=split_dir,
        )
        fold_rows.append(row)
        if segment_errors is not None:
            all_segment_errors.append(segment_errors)

    if not all_segment_errors:
        return None, fold_rows

    combined_segment_errors = pd.concat(all_segment_errors, ignore_index=True)
    combined_row, combined_flight_errors, combined_summary = _combined_summary_row(
        split_name=split_name,
        segment_errors=combined_segment_errors,
        args=args,
    )
    combined_segment_errors.to_csv(split_dir / "segment_errors.csv", index=False)
    combined_flight_errors.to_csv(split_dir / "flight_errors.csv", index=False)
    save_summary(combined_summary, split_dir / "summary.json")
    return combined_row, fold_rows


def main() -> None:
    """执行泛化能力基准实验。"""

    args = parse_args()
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    features_csv, feature_meta = _prepare_feature_view(args, output_dir)

    requested_features = _requested_features_for_preset(args.feature_preset)
    cleaned, feature_cols = _prepare_training_frame(features_csv, [args.target], requested_features)

    comparison_rows = []
    fold_rows = []
    for split_name in args.splits:
        combined_row, one_fold_rows = _run_one_split(
            split_name=split_name,
            cleaned=cleaned,
            feature_cols=feature_cols,
            args=args,
            output_dir=output_dir,
        )
        if combined_row is not None:
            comparison_rows.append(combined_row)
        fold_rows.extend(one_fold_rows)

    comparison = save_ablation_results(comparison_rows, output_dir / "comparison.csv")
    fold_metrics = save_ablation_results(fold_rows, output_dir / "fold_metrics.csv")
    best_by_energy = comparison.sort_values("flight_mean_abs_energy_error_pct").iloc[0].to_dict() if not comparison.empty else None
    worst_by_energy = comparison.sort_values("flight_mean_abs_energy_error_pct", ascending=False).iloc[0].to_dict() if not comparison.empty else None
    payload = {
        "input": str(_resolve_path(args.input)),
        "output_dir": str(output_dir.resolve()),
        "feature_view": feature_meta,
        "target": args.target,
        "target_mode": infer_target_mode(args.target),
        "method": args.method,
        "feature_preset": args.feature_preset,
        "splits": list(args.splits),
        "feature_count": len(feature_cols),
        "features": feature_cols,
        "test_size": args.test_size,
        "battery_wh": args.battery_wh,
        "phase_residual_correction": {
            "enabled": bool(args.phase_residual_correction),
            "phase_column": args.phase_column,
            "phase_min_rows": args.phase_min_rows,
            "phase_shrinkage_rows": args.phase_shrinkage_rows,
        },
        "best_by_flight_mean_abs_energy_error_pct": best_by_energy,
        "worst_by_flight_mean_abs_energy_error_pct": worst_by_energy,
        "outputs": {
            "comparison": str((output_dir / "comparison.csv").resolve()),
            "fold_metrics": str((output_dir / "fold_metrics.csv").resolve()),
            "summary": str((output_dir / "summary.json").resolve()),
        },
        "row_counts": {
            "comparison_rows": int(len(comparison.index)),
            "fold_rows": int(len(fold_metrics.index)),
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
