# 比较无人机质量字段解释假设，避免把数据集来源标签当成部署输入。
"""运行质量输入假设实验。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from uav_energy_engine.error_analysis import (
    build_flight_error_table,
    build_phase_error_table,
    build_segment_error_table_from_frame,
    summarize_error_tables,
)
from uav_energy_engine.altitude_profiles import ALTITUDE_PROFILES, apply_altitude_profile
from uav_energy_engine.evaluate import regression_metrics, save_ablation_results, save_summary
from uav_energy_engine.features import ensure_planned_ground_speed
from uav_energy_engine.model import _fit_model
from uav_energy_engine.planned_equivalent_features import (
    PLANNED_EQUIVALENT_WIND_FEATURE_COLUMNS,
    add_planned_equivalent_wind_features,
)
from uav_energy_engine.phase_expert import fit_phase_expert_model
from uav_energy_engine.phase_residual import wrap_with_categorical_residual_corrections
from uav_energy_engine.wind_profiles import WIND_PROFILES, apply_wind_profile


SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from audit_weight_semantics_and_constant_bias import build_bias_table, estimate_linear_sensitivity


MASS_ASSUMPTIONS = [
    "payload_only",
    "payload_plus_assumed_empty_mass",
    "payload_plus_estimated_base_mass",
]

SAMPLE_WEIGHT_POLICIES = [
    "none",
    "source_balanced",
    "phase_balanced",
    "source_phase_balanced",
]

EQUIVALENT_WIND_FEATURE_SETS = {
    "none": [],
    "airspeed": ["equivalent_airspeed_mps"],
    "components": [
        "equivalent_airspeed_mps",
        "equivalent_along_track_airspeed_mps",
        "equivalent_cross_track_airspeed_mps",
        "equivalent_crosswind_abs_mps",
        "tailwind_mps",
    ],
    "ratios": ["headwind_ratio", "crosswind_ratio", "tailwind_mps"],
    "all": list(PLANNED_EQUIVALENT_WIND_FEATURE_COLUMNS),
}

DEFAULT_ASSUMED_EMPTY_MASS_KG = {
    "m100": 2.355,
    "wemuav": 1.388,
}

BASE_DEPLOYMENT_FEATURES = [
    "planned_ground_speed_mps",
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
    "pressure_hpa",
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
    "horizontal_speed_std_mps",
    "horizontal_speed_p95_mps",
    "acceleration_abs_mean_mps2",
    "acceleration_abs_p95_mps2",
    "turn_rate_mean_deg_s",
    "turn_rate_p95_deg_s",
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

FORBIDDEN_FEATURE_EXACT = {
    "source_dataset",
    "source_data_type",
    "training_role",
    "source_case_id",
    "source_folder",
    "source_flight_file",
    "source_weather_file",
    "source_flight_type",
}
FORBIDDEN_FEATURE_PREFIXES = (
    "source_is_",
    "role_is_",
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="比较质量字段解释假设对预测误差和常量偏差的影响。")
    parser.add_argument(
        "--features",
        default="outputs/multi_source_training/combined_power_preflight_weather_complete.csv",
        help="多来源训练表 CSV",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/multi_source_training/mass_assumption_experiment",
        help="实验输出目录",
    )
    parser.add_argument("--target", default="mean_power_w", help="训练目标列")
    parser.add_argument("--method", default="gradient_boosting", help="训练方法")
    parser.add_argument("--group-col", default="flight", help="训练/测试分组列")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--battery-wh", type=float, default=130.0, help="风险评估使用的电池容量 Wh")
    parser.add_argument(
        "--sample-weight-policy",
        default="none",
        choices=SAMPLE_WEIGHT_POLICIES,
        help="训练样本权重策略；只用于训练集均衡，不作为部署输入",
    )
    parser.add_argument(
        "--exclude-features",
        nargs="*",
        default=[],
        help="从模型输入中排除的特征列，用于字段口径干预实验",
    )
    parser.add_argument(
        "--wind-profile",
        default="current",
        choices=WIND_PROFILES,
        help="风字段口径：current 保持原表，weather_basic 使用 hist_* 天气风，height_weather 使用高度层天气风",
    )
    parser.add_argument(
        "--altitude-profile",
        default="current",
        choices=ALTITUDE_PROFILES,
        help="高度字段口径：current 保持原表，planned_level 使用计划巡航高度并清零爬降动态量",
    )
    parser.add_argument(
        "--assumptions",
        nargs="+",
        default=MASS_ASSUMPTIONS,
        choices=MASS_ASSUMPTIONS,
        help="要比较的质量字段解释假设",
    )
    parser.add_argument(
        "--corrections",
        nargs="+",
        default=["none", "phase", "phase_expert"],
        choices=["none", "phase", "phase_expert"],
        help="允许的阶段策略；none 为无修正，phase 为阶段残差，phase_expert 为阶段专家模型",
    )
    parser.add_argument(
        "--assumed-empty-mass-kg",
        nargs="*",
        default=[f"{key}={value}" for key, value in DEFAULT_ASSUMED_EMPTY_MASS_KG.items()],
        help="已知/假设空机质量，格式如 m100=2.355 wemuav=1.388",
    )
    parser.add_argument(
        "--fallback-target-per-kg",
        type=float,
        default=120.0,
        help="载荷-目标敏感度不可靠时用于反推基础质量的兜底值；mean_power_w 下单位约为 W/kg",
    )
    parser.add_argument("--min-group-rows", type=int, default=5, help="阶段残差修正中单阶段最小行数")
    parser.add_argument("--min-expert-rows", type=int, default=20, help="阶段专家模型单阶段最小训练行数")
    parser.add_argument("--shrinkage-rows", type=float, default=20.0, help="阶段残差修正向全局偏差收缩的强度")
    parser.add_argument(
        "--equivalent-wind-feature-set",
        default="none",
        choices=sorted(EQUIVALENT_WIND_FEATURE_SETS),
        help="是否把飞前可计算的等效风特征加入训练；默认不加入，用于消融对照",
    )
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _safe_name(value: object) -> str:
    """转换为安全目录名。"""

    return str(value).replace("/", "_").replace(" ", "_").replace(":", "_")


def parse_source_float_map(items: Sequence[str]) -> dict[str, float]:
    """解析 source=value 形式的浮点参数。"""

    out: dict[str, float] = {}
    for item in items:
        if "=" not in str(item):
            raise ValueError(f"质量参数必须使用 source=value 格式: {item}")
        key, value = str(item).split("=", 1)
        key = key.strip().lower()
        if not key:
            raise ValueError(f"质量参数缺少数据源名: {item}")
        out[key] = float(value)
    return out


def _normalised_source(frame: pd.DataFrame) -> pd.Series:
    """读取数据源标签；仅用于填充缺失的无人机质量和输出诊断切片。"""

    if "source_dataset" not in frame.columns:
        return pd.Series("unknown", index=frame.index, dtype=object)
    return frame["source_dataset"].fillna("unknown").astype(str).str.lower()


def add_phase_onehot(frame: pd.DataFrame) -> pd.DataFrame:
    """把飞行阶段标签转换为可部署的 one-hot 数值特征。"""

    out = frame.copy()
    if "phase_label" not in out.columns:
        return out
    phases = out["phase_label"].fillna("unknown").astype(str)
    for phase in PHASE_LABELS:
        out[f"phase_is_{phase}"] = (phases == phase).astype(float)
    return out


def ensure_payload_kg(frame: pd.DataFrame) -> pd.DataFrame:
    """确保存在 payload_kg 列。"""

    out = frame.copy()
    if "payload_kg" not in out.columns and "payload_g" in out.columns:
        out["payload_kg"] = pd.to_numeric(out["payload_g"], errors="coerce") / 1000.0
    if "payload_kg" not in out.columns:
        out["payload_kg"] = 0.0
    out["payload_kg"] = pd.to_numeric(out["payload_kg"], errors="coerce").fillna(0.0)
    return out


def _map_source_values(frame: pd.DataFrame, values_by_source: dict[str, float], default_value: float = 0.0) -> pd.Series:
    """按数据源把质量参数填入表格。"""

    sources = _normalised_source(frame)
    values = sources.map(values_by_source)
    if values.isna().any():
        values = values.fillna(default_value)
    return pd.to_numeric(values, errors="coerce").fillna(default_value).astype(float)


def apply_mass_assumption(
    frame: pd.DataFrame,
    assumption: str,
    assumed_empty_mass_by_source: dict[str, float],
    estimated_base_mass_by_source: Optional[dict[str, float]] = None,
) -> tuple[pd.DataFrame, list[str], dict]:
    """按指定假设生成质量特征。"""

    if assumption not in MASS_ASSUMPTIONS:
        raise ValueError(f"不支持的质量假设: {assumption}")

    out = ensure_payload_kg(frame)
    meta = {
        "assumption": assumption,
        "uses_source_dataset_as_feature": False,
        "source_dataset_usage": "仅用于在离线数据集缺少机型配置时填充质量代理列，模型特征不包含 source_dataset。",
    }
    if assumption == "payload_only":
        return out, ["payload_kg"], meta

    if assumption == "payload_plus_assumed_empty_mass":
        empty_mass = _map_source_values(out, assumed_empty_mass_by_source, default_value=0.0)
        out["assumed_empty_mass_kg"] = empty_mass
        out["assumed_takeoff_mass_kg"] = empty_mass + out["payload_kg"]
        meta["assumed_empty_mass_by_source"] = dict(assumed_empty_mass_by_source)
        return out, ["payload_kg", "assumed_empty_mass_kg", "assumed_takeoff_mass_kg"], meta

    estimated = estimated_base_mass_by_source or {}
    default_estimated = float(np.nanmedian(list(estimated.values()))) if estimated else 0.0
    if not np.isfinite(default_estimated):
        default_estimated = 0.0
    estimated_mass = _map_source_values(out, estimated, default_value=default_estimated)
    out["estimated_empty_mass_kg"] = estimated_mass
    out["estimated_takeoff_mass_kg"] = estimated_mass + out["payload_kg"]
    meta["estimated_base_mass_by_source"] = dict(estimated)
    return out, ["payload_kg", "estimated_empty_mass_kg", "estimated_takeoff_mass_kg"], meta


def assert_no_source_features(feature_cols: Sequence[str]) -> None:
    """阻止把数据集来源标签作为部署特征。"""

    illegal = []
    for column in feature_cols:
        if column in FORBIDDEN_FEATURE_EXACT or any(column.startswith(prefix) for prefix in FORBIDDEN_FEATURE_PREFIXES):
            illegal.append(column)
    if illegal:
        raise ValueError("质量假设实验禁止使用数据源标签作为模型特征: {}".format(", ".join(sorted(illegal))))


def _available_numeric_features(frame: pd.DataFrame, requested: Sequence[str]) -> list[str]:
    """筛选当前表中可用且至少有一个有效值的数值特征。"""

    out = []
    for column in requested:
        if column not in frame.columns:
            continue
        series = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        if series.notna().sum() == 0:
            continue
        out.append(column)
    assert_no_source_features(out)
    return out


def feature_columns_for_assumption(
    frame: pd.DataFrame,
    mass_feature_cols: Sequence[str],
    exclude_features: Optional[Sequence[str]] = None,
    equivalent_wind_feature_set: str = "none",
) -> list[str]:
    """生成不含数据源标签的部署特征列。"""

    equivalent_features = EQUIVALENT_WIND_FEATURE_SETS.get(str(equivalent_wind_feature_set), [])
    requested = (
        BASE_DEPLOYMENT_FEATURES
        + equivalent_features
        + PHASE_ONEHOT_FEATURES
        + list(mass_feature_cols)
    )
    if "planned_ground_speed_mps" not in frame.columns and "speed_mps" in frame.columns:
        requested = ["speed_mps" if column == "planned_ground_speed_mps" else column for column in requested]
    excluded = {str(column) for column in (exclude_features or [])}
    return [column for column in _available_numeric_features(frame, requested) if column not in excluded]


def audit_mass_source_proxy_risk(frame: pd.DataFrame, mass_feature_cols: Sequence[str]) -> dict:
    """审计质量列是否在当前数据集中退化为数据源代理。"""

    if "source_dataset" not in frame.columns:
        return {
            "mass_source_proxy_risk": "unknown",
            "mass_source_proxy_reason": "缺少 source_dataset，无法做离线诊断。",
            "mass_source_proxy_columns": [],
            "mass_source_proxy_details": [],
        }

    details = []
    high_columns = []
    medium_columns = []
    sources = _normalised_source(frame)
    for column in mass_feature_cols:
        if column not in frame.columns:
            continue
        stats = []
        for source, group in frame.groupby(sources, sort=True):
            values = pd.to_numeric(group[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            if values.empty:
                stats.append(
                    {
                        "source_dataset": str(source),
                        "count": int(len(group.index)),
                        "unique_count": 0,
                        "min": None,
                        "max": None,
                        "median": None,
                    }
                )
                continue
            stats.append(
                {
                    "source_dataset": str(source),
                    "count": int(len(group.index)),
                    "unique_count": int(values.nunique(dropna=True)),
                    "min": float(values.min()),
                    "max": float(values.max()),
                    "median": float(values.median()),
                }
            )
        valid_stats = [row for row in stats if row["median"] is not None]
        constant_by_source = bool(valid_stats) and all(int(row["unique_count"]) <= 1 for row in valid_stats)
        distinct_medians = len({round(float(row["median"]), 6) for row in valid_stats}) == len(valid_stats)
        non_overlapping_ranges = False
        if len(valid_stats) >= 2:
            ordered = sorted(valid_stats, key=lambda row: float(row["min"]))
            non_overlapping_ranges = all(float(left["max"]) < float(right["min"]) for left, right in zip(ordered, ordered[1:]))
        column_risk = "low"
        if constant_by_source and distinct_medians:
            column_risk = "high"
            high_columns.append(column)
        elif non_overlapping_ranges:
            column_risk = "high"
            high_columns.append(column)
        elif distinct_medians:
            column_risk = "medium"
            medium_columns.append(column)
        details.append(
            {
                "column": column,
                "risk": column_risk,
                "constant_by_source": constant_by_source,
                "distinct_source_medians": distinct_medians,
                "non_overlapping_source_ranges": non_overlapping_ranges,
                "stats": stats,
            }
        )

    if high_columns:
        return {
            "mass_source_proxy_risk": "high",
            "mass_source_proxy_reason": "至少一个质量列在当前数据集中可按数值区分数据源/机型，模型可能把它当作来源代理，而不是学到连续质量规律。",
            "mass_source_proxy_columns": high_columns,
            "mass_source_proxy_details": details,
        }
    if medium_columns:
        return {
            "mass_source_proxy_risk": "medium",
            "mass_source_proxy_reason": "质量列的不同数据源中位数不同，存在弱来源代理风险。",
            "mass_source_proxy_columns": medium_columns,
            "mass_source_proxy_details": details,
        }
    return {
        "mass_source_proxy_risk": "low",
        "mass_source_proxy_reason": "当前质量列没有表现出明显来源代理风险。",
        "mass_source_proxy_columns": [],
        "mass_source_proxy_details": details,
    }


def _normalise_sample_weight(weights: pd.Series) -> pd.Series:
    """把样本权重归一化到均值约为 1。"""

    cleaned = pd.to_numeric(weights, errors="coerce").replace([np.inf, -np.inf], np.nan)
    if cleaned.notna().sum() == 0:
        return pd.Series(1.0, index=weights.index, dtype=float)
    cleaned = cleaned.fillna(float(cleaned.median())).clip(lower=1e-12)
    mean_value = float(cleaned.mean())
    if not np.isfinite(mean_value) or mean_value <= 1e-9:
        return pd.Series(1.0, index=weights.index, dtype=float)
    scaled = (cleaned / mean_value).clip(lower=0.05, upper=20.0)
    scaled_mean = float(scaled.mean())
    if not np.isfinite(scaled_mean) or scaled_mean <= 1e-9:
        return pd.Series(1.0, index=weights.index, dtype=float)
    return scaled / scaled_mean


def compute_sample_weight(frame: pd.DataFrame, policy: str) -> Optional[pd.Series]:
    """根据训练侧分布生成样本权重，避免样本量大的数据源或阶段吞掉小数据源。"""

    if policy == "none":
        return None
    if policy not in SAMPLE_WEIGHT_POLICIES:
        raise ValueError(f"不支持的样本权重策略: {policy}")

    if policy == "source_balanced":
        if "source_dataset" not in frame.columns:
            return None
        keys = _normalised_source(frame)
    elif policy == "phase_balanced":
        if "phase_label" not in frame.columns:
            return None
        keys = frame["phase_label"].fillna("unknown").astype(str)
    else:
        if "source_dataset" not in frame.columns or "phase_label" not in frame.columns:
            return None
        keys = _normalised_source(frame) + "|" + frame["phase_label"].fillna("unknown").astype(str)

    counts = keys.value_counts(dropna=False)
    if counts.empty:
        return None
    weights = keys.map(lambda key: 1.0 / max(float(counts.get(key, 1)), 1.0)).astype(float)
    return _normalise_sample_weight(weights)


def _clean_for_training(frame: pd.DataFrame, feature_cols: Sequence[str], target: str) -> pd.DataFrame:
    """按特征列和目标列清理训练/评估表。"""

    required = list(feature_cols) + [target]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("训练数据缺少必要列: {}".format(", ".join(missing)))
    cleaned = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=required).copy()
    if cleaned.empty:
        raise ValueError("训练数据经过清洗后为空。")
    return cleaned


def split_frame(
    frame: pd.DataFrame,
    group_col: Optional[str],
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """按飞行分组切分训练集和测试集。"""

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


def estimate_source_base_masses(
    train_frame: pd.DataFrame,
    target: str,
    feature_cols: Sequence[str],
    method: str,
    random_state: int,
    fallback_target_per_kg: float,
) -> tuple[dict[str, float], dict]:
    """从训练集常量残差粗略反推每个数据源可能缺失的基础质量。"""

    cleaned = _clean_for_training(train_frame, feature_cols, target)
    model = _fit_model(
        x_train=cleaned[list(feature_cols)].copy(),
        y_train=pd.to_numeric(cleaned[target], errors="coerce"),
        feature_cols=feature_cols,
        method=method,
        random_state=random_state,
        base_cols=[
            column
            for column in ["planned_ground_speed_mps", "speed_mps", "payload_kg", "altitude_m"]
            if column in feature_cols and not (column == "speed_mps" and "planned_ground_speed_mps" in feature_cols)
        ],
    )
    predictions = pd.Series(np.asarray(model.predict(cleaned), dtype=float).reshape(-1), index=cleaned.index)
    residual = pd.to_numeric(cleaned[target], errors="coerce") - predictions
    sensitivity = estimate_linear_sensitivity(cleaned, "payload_kg", target)
    slope = float(sensitivity.get("slope", np.nan))
    r2 = float(sensitivity.get("r2", np.nan))
    slope_source = "payload_linear_sensitivity"
    if not np.isfinite(slope) or slope <= 1e-9 or not np.isfinite(r2) or r2 < 0.30:
        slope = float(fallback_target_per_kg)
        slope_source = "fallback"
    if slope <= 1e-9:
        slope = 1.0
        slope_source = "fallback_clipped"

    frame = cleaned.copy()
    frame["_residual_for_mass_estimation"] = residual
    estimates: dict[str, float] = {}
    rows = []
    for source, group in frame.groupby(_normalised_source(frame), sort=True):
        residual_bias = float(pd.to_numeric(group["_residual_for_mass_estimation"], errors="coerce").mean())
        estimated_mass = max(0.0, residual_bias / slope)
        estimates[str(source)] = float(estimated_mass)
        rows.append(
            {
                "source_dataset": str(source),
                "count": int(len(group.index)),
                "residual_bias_target_unit": residual_bias,
                "target_per_kg_used": float(slope),
                "estimated_base_mass_kg": float(estimated_mass),
            }
        )

    meta = {
        "target_per_kg_used": float(slope),
        "target_per_kg_source": slope_source,
        "payload_sensitivity": sensitivity,
        "estimated_base_mass_by_source": estimates,
        "estimated_base_mass_rows": rows,
        "note": "这是训练侧字段语义诊断，不等同真实空机重量；负向残差不会被解释为负质量。",
    }
    return estimates, meta


def _source_error_metrics(segment_errors: pd.DataFrame) -> dict:
    """按数据源生成摘要指标，数据源只用于诊断输出。"""

    if "source_dataset" not in segment_errors.columns:
        return {}
    source_rows = []
    out = {}
    for source, group in segment_errors.groupby("source_dataset", sort=True):
        actual = pd.to_numeric(group["actual_target_value"], errors="coerce")
        predicted = pd.to_numeric(group["predicted_target_value"], errors="coerce")
        metrics = regression_metrics(actual.to_numpy(dtype=float), predicted.to_numpy(dtype=float))
        target_bias = float(pd.to_numeric(group["target_error"], errors="coerce").mean())
        mean_abs_target_pct = float(pd.to_numeric(group["abs_target_error_pct"], errors="coerce").mean())
        mean_abs_energy_pct = float(pd.to_numeric(group["abs_segment_energy_error_pct"], errors="coerce").mean())
        source_rows.append(
            {
                "source_dataset": str(source),
                "target_bias": target_bias,
                "target_rmse": metrics["rmse"],
                "mean_abs_target_error_pct": mean_abs_target_pct,
                "mean_abs_energy_error_pct": mean_abs_energy_pct,
            }
        )
        prefix = f"source_{_safe_name(source)}"
        out[f"{prefix}_count"] = int(len(group.index))
        out[f"{prefix}_target_bias"] = target_bias
        out[f"{prefix}_target_rmse"] = metrics["rmse"]
        out[f"{prefix}_mean_abs_target_error_pct"] = mean_abs_target_pct
        out[f"{prefix}_mean_abs_energy_error_pct"] = mean_abs_energy_pct
    if source_rows:
        source_frame = pd.DataFrame(source_rows)
        out["balanced_source_target_rmse"] = float(pd.to_numeric(source_frame["target_rmse"], errors="coerce").mean())
        out["worst_source_target_rmse"] = float(pd.to_numeric(source_frame["target_rmse"], errors="coerce").max())
        out["balanced_abs_source_target_bias"] = float(
            pd.to_numeric(source_frame["target_bias"], errors="coerce").abs().mean()
        )
        out["worst_abs_source_target_bias"] = float(pd.to_numeric(source_frame["target_bias"], errors="coerce").abs().max())
        out["balanced_source_abs_target_error_pct"] = float(
            pd.to_numeric(source_frame["mean_abs_target_error_pct"], errors="coerce").mean()
        )
        out["worst_source_abs_target_error_pct"] = float(
            pd.to_numeric(source_frame["mean_abs_target_error_pct"], errors="coerce").max()
        )
    return out


def add_deployment_selection_score(comparison: pd.DataFrame) -> pd.DataFrame:
    """增加部署导向评分，避免只按单个离线指标选择默认策略。"""

    if comparison.empty:
        return comparison
    out = comparison.copy()
    metric_weights = {
        "segment_rmse": 0.20,
        "flight_mean_abs_energy_error_pct": 0.30,
        "range_mean_abs_error_pct": 0.25,
        "worst_source_abs_target_error_pct": 0.20,
        "max_abs_source_phase_bias_w": 0.05,
    }
    risk_penalty = {"low": 0.0, "medium": 0.05, "high": 0.15, "unknown": 0.10}
    score = pd.Series(0.0, index=out.index, dtype=float)
    available_weight = 0.0
    for column, weight in metric_weights.items():
        if column not in out.columns:
            continue
        values = pd.to_numeric(out[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        if values.notna().sum() == 0:
            continue
        minimum = float(values.min())
        maximum = float(values.max())
        if maximum == minimum:
            normalized = pd.Series(0.0, index=out.index, dtype=float)
        else:
            normalized = (values - minimum) / (maximum - minimum)
        score = score + normalized.fillna(1.0) * weight
        available_weight += weight
    if available_weight > 0:
        score = score / available_weight
    if "mass_source_proxy_risk" in out.columns:
        score = score + out["mass_source_proxy_risk"].fillna("unknown").map(risk_penalty).fillna(0.10)
    out["deployment_selection_score"] = score
    out["deployment_selection_score_note"] = (
        "越低越适合做默认部署候选；综合段级误差、任务电量误差、航程误差、最差数据源误差和来源代理风险。"
    )
    return out


def _summary_row(
    variant: str,
    assumption: str,
    correction: str,
    feature_cols: Sequence[str],
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    segment_errors: pd.DataFrame,
    flight_errors: pd.DataFrame,
    summary: dict,
    mass_meta: dict,
    sample_weight_policy: str,
    sample_weight: Optional[pd.Series],
    equivalent_wind_feature_set: str = "none",
) -> dict:
    """压平一个质量假设实验结果。"""

    segment = summary["segment"]
    flight = summary["flight"]
    risk = summary.get("risk", {})
    bias_table = build_bias_table(segment_errors.assign(variant=variant))
    source_phase = bias_table.loc[bias_table["group_type"] == "source_phase"].copy()
    max_source_phase_bias = (
        float(pd.to_numeric(source_phase["prediction_bias_w"], errors="coerce").abs().max())
        if not source_phase.empty
        else float("nan")
    )
    row = {
        "variant": variant,
        "mass_assumption": assumption,
        "correction": correction,
        "sample_weight_policy": sample_weight_policy,
        "equivalent_wind_feature_set": equivalent_wind_feature_set,
        "uses_source_dataset_as_feature": False,
        "feature_count": int(len(feature_cols)),
        "features": ",".join(feature_cols),
        "train_count": int(len(train_frame.index)),
        "test_count": int(len(test_frame.index)),
        "segment_rmse": segment.get("rmse"),
        "segment_mae": segment.get("mae"),
        "segment_r2": segment.get("r2"),
        "segment_target_bias": float(pd.to_numeric(segment_errors["target_error"], errors="coerce").mean()),
        "segment_mean_abs_target_error_pct": segment.get("mean_abs_target_error_pct"),
        "flight_mean_abs_energy_error_wh": flight.get("mean_abs_energy_error_wh"),
        "flight_mean_abs_energy_error_pct": flight.get("mean_abs_energy_error_pct"),
        "range_mean_abs_error_pct": flight.get("mean_abs_range_error_pct"),
        "max_abs_source_phase_bias_w": max_source_phase_bias,
        "mass_source_proxy_risk": mass_meta.get("mass_source_proxy_risk"),
        "mass_source_proxy_columns": ",".join(mass_meta.get("mass_source_proxy_columns", [])),
        "range_overprediction_gt_25pct_count": risk.get("range_overprediction_gt_25pct_count"),
        "energy_underprediction_gt_25pct_count": risk.get("energy_underprediction_gt_25pct_count"),
        "mass_meta": json.dumps(mass_meta, ensure_ascii=False, sort_keys=True),
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
    row.update(_source_error_metrics(segment_errors))
    return row


def run_variant(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    split_meta: dict,
    assumption: str,
    correction: str,
    args: argparse.Namespace,
    output_dir: Path,
    assumed_empty_mass_by_source: dict[str, float],
    estimated_base_mass_by_source: Optional[dict[str, float]] = None,
    mass_meta_extra: Optional[dict] = None,
) -> dict:
    """训练并评估一个质量假设变体。"""

    sample_weight_policy = getattr(args, "sample_weight_policy", "none")
    wind_profile = getattr(args, "wind_profile", "current")
    altitude_profile = getattr(args, "altitude_profile", "current")
    equivalent_wind_feature_set = getattr(args, "equivalent_wind_feature_set", "none")
    variant = f"{assumption}__{correction}"
    if sample_weight_policy != "none":
        variant = f"{variant}__weight_{sample_weight_policy}"
    if wind_profile != "current":
        variant = f"{variant}__wind_{wind_profile}"
    if altitude_profile != "current":
        variant = f"{variant}__altitude_{altitude_profile}"
    if equivalent_wind_feature_set != "none":
        variant = f"{variant}__equivwind_{equivalent_wind_feature_set}"
    variant_dir = output_dir / _safe_name(variant)
    variant_dir.mkdir(parents=True, exist_ok=True)

    train_mass, mass_feature_cols, mass_meta = apply_mass_assumption(
        train_frame,
        assumption=assumption,
        assumed_empty_mass_by_source=assumed_empty_mass_by_source,
        estimated_base_mass_by_source=estimated_base_mass_by_source,
    )
    test_mass, _, _ = apply_mass_assumption(
        test_frame,
        assumption=assumption,
        assumed_empty_mass_by_source=assumed_empty_mass_by_source,
        estimated_base_mass_by_source=estimated_base_mass_by_source,
    )
    if mass_meta_extra:
        mass_meta.update(mass_meta_extra)

    excluded_features = list(getattr(args, "exclude_features", []) or [])
    feature_cols = feature_columns_for_assumption(
        train_mass,
        mass_feature_cols,
        exclude_features=excluded_features,
        equivalent_wind_feature_set=equivalent_wind_feature_set,
    )
    proxy_audit = audit_mass_source_proxy_risk(train_mass, mass_feature_cols)
    mass_meta.update(proxy_audit)
    train_clean = _clean_for_training(train_mass, feature_cols, args.target)
    test_clean = _clean_for_training(test_mass, feature_cols, args.target)
    assert_no_source_features(feature_cols)
    sample_weight = compute_sample_weight(train_clean, sample_weight_policy)

    base_cols = [
        column
        for column in [
            "planned_ground_speed_mps",
            "payload_kg",
            "assumed_takeoff_mass_kg",
            "estimated_takeoff_mass_kg",
            "altitude_m",
        ]
        if column in feature_cols
    ]
    if correction == "phase_expert":
        model = fit_phase_expert_model(
            train_frame=train_clean,
            target=args.target,
            feature_cols=feature_cols,
            method=args.method,
            random_state=args.random_state,
            phase_col="phase_label",
            min_expert_rows=args.min_expert_rows,
            base_cols=base_cols,
            sample_weight=sample_weight,
        )
    else:
        model = _fit_model(
            x_train=train_clean[list(feature_cols)].copy(),
            y_train=pd.to_numeric(train_clean[args.target], errors="coerce"),
            feature_cols=feature_cols,
            method=args.method,
            random_state=args.random_state,
            base_cols=base_cols,
            sample_weight=sample_weight,
        )
    if correction == "phase":
        model = wrap_with_categorical_residual_corrections(
            base_model=model,
            train_frame=train_clean,
            target=args.target,
            correction_groups=[["phase_label"]],
            min_group_rows=args.min_group_rows,
            shrinkage_rows=args.shrinkage_rows,
        )
    elif correction not in {"none", "phase_expert"}:
        raise ValueError(f"不支持的修正策略: {correction}")

    segment_errors, segment_meta = build_segment_error_table_from_frame(
        model=model,
        test_frame=test_clean,
        target=args.target,
        segment_meta={
            **split_meta,
            "target": args.target,
            "features": list(feature_cols),
            "excluded_features": excluded_features,
            "mass_assumption": assumption,
            "correction": correction,
            "sample_weight_policy": sample_weight_policy,
            "wind_profile": wind_profile,
            "altitude_profile": altitude_profile,
            "equivalent_wind_feature_set": equivalent_wind_feature_set,
            "uses_source_dataset_as_feature": False,
            "expert_col": "phase_label" if correction == "phase_expert" else None,
            "expert_counts": dict(getattr(model, "expert_counts", {})),
            "experts": sorted(list(getattr(model, "experts", {}).keys())),
            "mass_meta": mass_meta,
        },
    )
    segment_errors["variant"] = variant
    flight_errors = build_flight_error_table(segment_errors, battery_wh=args.battery_wh, group_col="flight")
    phase_errors = build_phase_error_table(segment_errors) if "phase_label" in segment_errors.columns else pd.DataFrame()
    bias_table = build_bias_table(segment_errors)
    summary = summarize_error_tables(segment_errors, flight_errors, segment_meta, battery_wh=args.battery_wh)

    train_clean.to_csv(variant_dir / "train_frame.csv", index=False)
    test_clean.to_csv(variant_dir / "test_frame.csv", index=False)
    segment_errors.to_csv(variant_dir / "segment_errors.csv", index=False)
    flight_errors.to_csv(variant_dir / "flight_errors.csv", index=False)
    bias_table.to_csv(variant_dir / "constant_bias_by_group.csv", index=False)
    if not phase_errors.empty:
        phase_errors.to_csv(variant_dir / "phase_errors.csv", index=False)
    save_summary(
        {
            "variant": variant,
            "mass_assumption": assumption,
            "correction": correction,
            "sample_weight_policy": sample_weight_policy,
            "wind_profile": wind_profile,
            "altitude_profile": altitude_profile,
            "equivalent_wind_feature_set": equivalent_wind_feature_set,
            "features": list(feature_cols),
            "excluded_features": excluded_features,
            "uses_source_dataset_as_feature": False,
            "expert_col": "phase_label" if correction == "phase_expert" else None,
            "expert_counts": dict(getattr(model, "expert_counts", {})),
            "experts": sorted(list(getattr(model, "experts", {}).keys())),
            "mass_meta": mass_meta,
            "summary": summary,
            "outputs": {
                "segment_errors": str((variant_dir / "segment_errors.csv").resolve()),
                "flight_errors": str((variant_dir / "flight_errors.csv").resolve()),
                "constant_bias_by_group": str((variant_dir / "constant_bias_by_group.csv").resolve()),
            },
        },
        variant_dir / "summary.json",
    )
    return _summary_row(
        variant=variant,
        assumption=assumption,
        correction=correction,
        feature_cols=feature_cols,
        train_frame=train_clean,
        test_frame=test_clean,
        segment_errors=segment_errors,
        flight_errors=flight_errors,
        summary=summary,
        mass_meta=mass_meta,
        sample_weight_policy=sample_weight_policy,
        sample_weight=sample_weight,
        equivalent_wind_feature_set=equivalent_wind_feature_set,
    )


def main() -> None:
    """执行质量输入假设实验。"""

    args = parse_args()
    input_path = _resolve_path(args.features)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    assumed_empty_mass_by_source = parse_source_float_map(args.assumed_empty_mass_kg)

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

    payload_only_train, payload_mass_features, _ = apply_mass_assumption(
        train_frame,
        assumption="payload_only",
        assumed_empty_mass_by_source=assumed_empty_mass_by_source,
    )
    payload_only_features = feature_columns_for_assumption(
        payload_only_train,
        payload_mass_features,
        exclude_features=args.exclude_features,
        equivalent_wind_feature_set=args.equivalent_wind_feature_set,
    )
    estimated_base_mass_by_source, estimated_meta = estimate_source_base_masses(
        train_frame=payload_only_train,
        target=args.target,
        feature_cols=payload_only_features,
        method=args.method,
        random_state=args.random_state,
        fallback_target_per_kg=args.fallback_target_per_kg,
    )

    rows = []
    for assumption in args.assumptions:
        for correction in args.corrections:
            mass_meta_extra = None
            estimated = None
            if assumption == "payload_plus_estimated_base_mass":
                estimated = estimated_base_mass_by_source
                mass_meta_extra = estimated_meta
            rows.append(
                run_variant(
                    train_frame=train_frame,
                    test_frame=test_frame,
                    split_meta=split_meta,
                    assumption=assumption,
                    correction=correction,
                    args=args,
                    output_dir=output_dir,
                    assumed_empty_mass_by_source=assumed_empty_mass_by_source,
                    estimated_base_mass_by_source=estimated,
                    mass_meta_extra=mass_meta_extra,
                )
            )

    comparison = add_deployment_selection_score(pd.DataFrame(rows))
    comparison = save_ablation_results(comparison.to_dict(orient="records"), output_dir / "comparison.csv")
    best_by_rmse = comparison.sort_values("segment_rmse").iloc[0].to_dict() if not comparison.empty else None
    best_by_deployment_score = (
        comparison.sort_values("deployment_selection_score").iloc[0].to_dict()
        if "deployment_selection_score" in comparison.columns and not comparison.empty
        else None
    )
    best_by_bias = (
        comparison.sort_values("max_abs_source_phase_bias_w").iloc[0].to_dict()
        if not comparison.empty
        else None
    )
    best_by_balanced_source_rmse = (
        comparison.sort_values("balanced_source_target_rmse").iloc[0].to_dict()
        if "balanced_source_target_rmse" in comparison.columns and not comparison.empty
        else None
    )
    best_by_worst_source_rmse = (
        comparison.sort_values("worst_source_target_rmse").iloc[0].to_dict()
        if "worst_source_target_rmse" in comparison.columns and not comparison.empty
        else None
    )
    payload = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "target": args.target,
        "method": args.method,
        "sample_weight_policy": args.sample_weight_policy,
        "wind_profile": args.wind_profile,
        "wind_profile_meta": wind_profile_meta,
        "altitude_profile": args.altitude_profile,
        "altitude_profile_meta": altitude_profile_meta,
        "equivalent_wind_feature_set": args.equivalent_wind_feature_set,
        "equivalent_wind_features": EQUIVALENT_WIND_FEATURE_SETS[args.equivalent_wind_feature_set],
        "excluded_features": args.exclude_features,
        "split": split_meta,
        "assumptions": args.assumptions,
        "corrections": args.corrections,
        "assumed_empty_mass_by_source": assumed_empty_mass_by_source,
        "estimated_base_mass_meta": estimated_meta,
        "row_counts": {
            "input": int(len(frame.index)),
            "train": int(len(train_frame.index)),
            "test": int(len(test_frame.index)),
            "comparison": int(len(comparison.index)),
        },
        "guardrails": {
            "uses_source_dataset_as_feature": False,
            "allowed_corrections": ["none", "phase", "phase_expert"],
            "forbidden_feature_exact": sorted(FORBIDDEN_FEATURE_EXACT),
            "forbidden_feature_prefixes": list(FORBIDDEN_FEATURE_PREFIXES),
        },
        "best_by_segment_rmse": best_by_rmse,
        "best_by_deployment_selection_score": best_by_deployment_score,
        "best_by_max_abs_source_phase_bias": best_by_bias,
        "best_by_balanced_source_rmse": best_by_balanced_source_rmse,
        "best_by_worst_source_rmse": best_by_worst_source_rmse,
        "outputs": {
            "comparison": str((output_dir / "comparison.csv").resolve()),
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
