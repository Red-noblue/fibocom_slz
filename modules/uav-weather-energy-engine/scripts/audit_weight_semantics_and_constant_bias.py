# 审计重量字段语义和常量预测偏差，帮助判断误差是否来自输入字段问题。
"""训练侧重量语义与常量偏差审计。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd

from uav_energy_engine.evaluate import save_summary
from uav_energy_engine.field_semantics import dataset_semantic_catalog, field_semantic_catalog


DEFAULT_VARIANT = "physical_source_flags__source_phase_joint__weight_distance_duration"
DEFAULT_MIN_PAYLOAD_SLOPE_R2 = 0.30
MIN_PAYLOAD_SLOPE_SAMPLE_COUNT = 3
MIN_PAYLOAD_UNIQUE_COUNT = 2
GROUP_SPECS = {
    "global": [],
    "source": ["source_dataset"],
    "phase": ["phase_label"],
    "source_phase": ["source_dataset", "phase_label"],
}


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="审计重量字段语义和常量预测偏差。")
    parser.add_argument(
        "--features",
        default="outputs/multi_source_training/combined_power_preflight_weather_complete.csv",
        help="多来源训练特征表 CSV",
    )
    parser.add_argument(
        "--benchmark-dir",
        default="outputs/multi_source_training/robustness_phase_strategy_benchmark",
        help="多随机种子误差基准目录",
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        default=[DEFAULT_VARIANT],
        help="要审计的变体名；传入 all 表示审计全部变体",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/multi_source_training/weight_semantics_bias_audit",
        help="审计输出目录",
    )
    parser.add_argument("--min-count", type=int, default=10, help="列入假设表的最小误差样本数")
    parser.add_argument("--min-bias-share", type=float, default=0.25, help="列入假设表的最小常量偏差占比")
    parser.add_argument(
        "--min-payload-slope-r2",
        type=float,
        default=DEFAULT_MIN_PAYLOAD_SLOPE_R2,
        help="允许用载荷-功率斜率反推等效重量的最小 R2",
    )
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _parse_random_state(path: Path) -> Optional[int]:
    """从 seed_XXX 目录名中解析随机种子。"""

    for parent in path.parents:
        name = parent.name
        if not name.startswith("seed_"):
            continue
        try:
            return int(name[len("seed_") :])
        except ValueError:
            return None
    return None


def _read_segment_errors(benchmark_dir: Path, variants: Sequence[str]) -> pd.DataFrame:
    """读取多随机种子输出中的分段误差表。"""

    selected = set(variants)
    allow_all = "all" in selected
    frames = []
    for path in sorted(benchmark_dir.glob("seed_*/**/segment_errors.csv")):
        variant = path.parent.name
        if not allow_all and variant not in selected:
            continue
        frame = pd.read_csv(path)
        frame["variant"] = variant
        frame["random_state"] = _parse_random_state(path)
        frame["segment_errors_path"] = str(path.resolve())
        frames.append(frame)

    direct_paths = []
    for variant in selected:
        if variant == "all":
            continue
        direct_path = benchmark_dir / variant / "segment_errors.csv"
        if direct_path.exists():
            direct_paths.append(direct_path)
    for path in direct_paths:
        variant = path.parent.name
        frame = pd.read_csv(path)
        frame["variant"] = variant
        frame["random_state"] = None
        frame["segment_errors_path"] = str(path.resolve())
        frames.append(frame)

    if not frames:
        raise FileNotFoundError(f"没有找到匹配的 segment_errors.csv: {benchmark_dir}")
    return pd.concat(frames, ignore_index=True)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    """安全读取数值列。"""

    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _rmse(values: pd.Series) -> float:
    """计算均方根误差。"""

    clean = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if clean.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(np.square(clean))))


def estimate_linear_sensitivity(frame: pd.DataFrame, x_col: str, y_col: str) -> dict:
    """估计 y 对 x 的一阶线性敏感度。"""

    if x_col not in frame.columns or y_col not in frame.columns:
        return {
            "slope": float("nan"),
            "intercept": float("nan"),
            "r2": float("nan"),
            "sample_count": 0,
            "unique_x_count": 0,
        }

    x = pd.to_numeric(frame[x_col], errors="coerce")
    y = pd.to_numeric(frame[y_col], errors="coerce")
    valid = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    x_valid = x.loc[valid].to_numpy(dtype=float)
    y_valid = y.loc[valid].to_numpy(dtype=float)
    unique_x_count = int(pd.Series(x_valid).nunique()) if x_valid.size else 0
    if x_valid.size < 3 or unique_x_count < 2:
        return {
            "slope": float("nan"),
            "intercept": float("nan"),
            "r2": float("nan"),
            "sample_count": int(x_valid.size),
            "unique_x_count": unique_x_count,
        }

    slope, intercept = np.polyfit(x_valid, y_valid, deg=1)
    predicted = slope * x_valid + intercept
    ss_res = float(np.sum(np.square(y_valid - predicted)))
    ss_tot = float(np.sum(np.square(y_valid - np.mean(y_valid))))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float("nan")
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r2": float(r2),
        "sample_count": int(x_valid.size),
        "unique_x_count": unique_x_count,
    }


def _bias_level(bias_share_of_rmse: float) -> str:
    """把常量偏差占比转换为风险等级。"""

    if not np.isfinite(bias_share_of_rmse):
        return "unknown"
    if bias_share_of_rmse >= 0.50:
        return "high"
    if bias_share_of_rmse >= 0.25:
        return "medium"
    return "low"


def _payload_sensitivity_status(
    slope: float,
    r2: float,
    sample_count: int,
    unique_x_count: int,
    min_r2: float = DEFAULT_MIN_PAYLOAD_SLOPE_R2,
) -> str:
    """判断载荷-功率敏感度是否足以反推重量。"""

    if sample_count < MIN_PAYLOAD_SLOPE_SAMPLE_COUNT or unique_x_count < MIN_PAYLOAD_UNIQUE_COUNT:
        return "insufficient_payload_variation"
    if not np.isfinite(slope) or not np.isfinite(r2):
        return "unavailable"
    if slope <= 1e-9:
        return "non_positive_slope"
    if r2 < min_r2:
        return "low_r2"
    return "reliable"


def _payload_semantic_lookup() -> dict[str, dict]:
    """整理 payload 字段在各数据集中的已知语义。"""

    out = {}
    for dataset in ["m100", "wemuav"]:
        rows = field_semantic_catalog(dataset)
        payload_rows = [row for row in rows if row.get("column") == "payload"]
        if payload_rows:
            out[dataset] = payload_rows[0]
    return out


def build_payload_semantics(features: pd.DataFrame) -> pd.DataFrame:
    """按数据源汇总载荷字段语义和分布。"""

    semantics = _payload_semantic_lookup()
    dataset_catalog = dataset_semantic_catalog()
    rows = []
    if "source_dataset" not in features.columns:
        return pd.DataFrame(rows)

    for source, group in features.groupby("source_dataset", sort=False):
        source_name = str(source)
        payload_kg = _numeric(group, "payload_kg")
        payload_g = _numeric(group, "payload_g")
        semantic = semantics.get(source_name, {})
        dataset_info = dataset_catalog.get(source_name, {})
        rows.append(
            {
                "source_dataset": source_name,
                "vehicle": dataset_info.get("vehicle"),
                "rows": int(len(group.index)),
                "payload_kg_coverage": float(payload_kg.notna().mean()) if len(group.index) else float("nan"),
                "payload_kg_min": float(payload_kg.min()) if payload_kg.notna().any() else float("nan"),
                "payload_kg_median": float(payload_kg.median()) if payload_kg.notna().any() else float("nan"),
                "payload_kg_max": float(payload_kg.max()) if payload_kg.notna().any() else float("nan"),
                "payload_kg_unique_count": int(payload_kg.nunique(dropna=True)),
                "payload_g_min": float(payload_g.min()) if payload_g.notna().any() else float("nan"),
                "payload_g_max": float(payload_g.max()) if payload_g.notna().any() else float("nan"),
                "payload_semantic": semantic.get("meaning_zh"),
                "payload_canonical": semantic.get("canonical"),
                "payload_model_use": semantic.get("model_use"),
                "payload_risk_level": semantic.get("risk_level"),
                "direct_training_use": dataset_info.get("direct_training_use"),
                "caution": dataset_info.get("caution"),
            }
        )
    return pd.DataFrame(rows)


def _group_key(row: pd.Series, group_cols: Sequence[str]) -> str:
    """生成可读分组名。"""

    if not group_cols:
        return "all"
    return " / ".join(str(row.get(column, "unknown")) for column in group_cols)


def _unique_segment_count(frame: pd.DataFrame) -> Optional[int]:
    """计算去重后的真实分段数。"""

    keys = [column for column in ["flight", "segment_id"] if column in frame.columns]
    if not keys:
        return None
    return int(frame[keys].astype(str).drop_duplicates().shape[0])


def _bias_row(
    group: pd.DataFrame,
    variant: str,
    group_type: str,
    group_cols: Sequence[str],
    min_payload_slope_r2: float = DEFAULT_MIN_PAYLOAD_SLOPE_R2,
) -> dict:
    """构造一个分组的常量偏差审计行。"""

    target_error = _numeric(group, "target_error")
    actual = _numeric(group, "actual_target_value")
    predicted = _numeric(group, "predicted_target_value")
    abs_target_pct = _numeric(group, "abs_target_error_pct")
    energy_error_pct = _numeric(group, "segment_energy_error_pct")
    prediction_bias_w = float(target_error.mean())
    target_rmse_w = _rmse(target_error)
    bias_share = abs(prediction_bias_w) / target_rmse_w if np.isfinite(target_rmse_w) and target_rmse_w > 1e-9 else float("nan")
    sensitivity = estimate_linear_sensitivity(group, "payload_kg", "actual_target_value")
    slope = float(sensitivity["slope"])
    sensitivity_status = _payload_sensitivity_status(
        slope=slope,
        r2=float(sensitivity["r2"]),
        sample_count=int(sensitivity["sample_count"]),
        unique_x_count=int(sensitivity["unique_x_count"]),
        min_r2=min_payload_slope_r2,
    )
    equivalent_payload_shift_kg = prediction_bias_w / slope if sensitivity_status == "reliable" else float("nan")
    possible_missing_mass_kg = (
        abs(equivalent_payload_shift_kg)
        if np.isfinite(equivalent_payload_shift_kg) and equivalent_payload_shift_kg < 0.0
        else float("nan")
    )
    speed_series = _numeric(group, "planned_ground_speed_mps")
    if speed_series.notna().sum() == 0:
        speed_series = _numeric(group, "speed_mps")
    first_row = group.iloc[0]
    row = {
        "variant": variant,
        "group_type": group_type,
        "group_key": _group_key(first_row, group_cols),
        "count": int(len(group.index)),
        "unique_segment_count": _unique_segment_count(group),
        "seed_count": int(group["random_state"].nunique()) if "random_state" in group.columns else None,
        "source_dataset": first_row.get("source_dataset") if "source_dataset" in group.columns else None,
        "phase_label": first_row.get("phase_label") if "phase_label" in group.columns else None,
        "prediction_bias_w": prediction_bias_w,
        "actual_minus_predicted_bias_w": -prediction_bias_w,
        "target_mae_w": float(target_error.abs().mean()),
        "target_rmse_w": target_rmse_w,
        "target_error_std_w": float(target_error.std(ddof=0)),
        "bias_share_of_rmse": float(bias_share),
        "constant_bias_level": _bias_level(bias_share),
        "mean_abs_target_error_pct": float(abs_target_pct.mean()),
        "p95_abs_target_error_pct": float(abs_target_pct.quantile(0.95)),
        "mean_segment_energy_error_pct": float(energy_error_pct.mean()),
        "actual_power_mean_w": float(actual.mean()),
        "predicted_power_mean_w": float(predicted.mean()),
        "payload_kg_mean": float(_numeric(group, "payload_kg").mean()),
        "payload_kg_min": float(_numeric(group, "payload_kg").min()),
        "payload_kg_max": float(_numeric(group, "payload_kg").max()),
        "payload_kg_unique_count": int(_numeric(group, "payload_kg").nunique(dropna=True)),
        "payload_power_slope_w_per_kg": slope,
        "payload_power_slope_r2": float(sensitivity["r2"]),
        "payload_slope_sample_count": int(sensitivity["sample_count"]),
        "payload_slope_unique_count": int(sensitivity["unique_x_count"]),
        "payload_sensitivity_status": sensitivity_status,
        "payload_sensitivity_min_r2": float(min_payload_slope_r2),
        "payload_sensitivity_reliable": sensitivity_status == "reliable",
        "equivalent_payload_shift_kg": float(equivalent_payload_shift_kg),
        "possible_missing_mass_kg": float(possible_missing_mass_kg),
        "mean_planned_ground_speed_mps": float(speed_series.mean()),
        "mean_altitude_m": float(_numeric(group, "altitude_m").mean()),
        "mean_duration_s": float(_numeric(group, "duration_s").mean()),
        "mean_distance_m": float(_numeric(group, "distance_m").mean()),
    }
    return row


def build_bias_table(
    segment_errors: pd.DataFrame,
    min_payload_slope_r2: float = DEFAULT_MIN_PAYLOAD_SLOPE_R2,
) -> pd.DataFrame:
    """按全局、数据源、阶段和数据源阶段汇总常量偏差。"""

    rows = []
    for variant, variant_group in segment_errors.groupby("variant", sort=False):
        for group_type, group_cols in GROUP_SPECS.items():
            available_cols = [column for column in group_cols if column in variant_group.columns]
            if group_cols and len(available_cols) != len(group_cols):
                continue
            if not group_cols:
                rows.append(
                    _bias_row(
                        variant_group,
                        str(variant),
                        group_type,
                        [],
                        min_payload_slope_r2=min_payload_slope_r2,
                    )
                )
                continue
            for _, group in variant_group.groupby(available_cols, sort=True):
                rows.append(
                    _bias_row(
                        group,
                        str(variant),
                        group_type,
                        available_cols,
                        min_payload_slope_r2=min_payload_slope_r2,
                    )
                )
    return pd.DataFrame(rows)


def _hypothesis_action(row: pd.Series) -> str:
    """根据偏差与载荷敏感度生成训练侧建议。"""

    source = str(row.get("source_dataset") or "")
    payload_unique = int(row.get("payload_kg_unique_count") or 0)
    slope = float(row.get("payload_power_slope_w_per_kg", float("nan")))
    equivalent_shift = float(row.get("equivalent_payload_shift_kg", float("nan")))
    bias = float(row.get("prediction_bias_w", float("nan")))
    sensitivity_status = str(row.get("payload_sensitivity_status") or "unknown")

    actions = []
    if source == "m100":
        actions.append("M100 的 payload_kg 已知是挂载包裹质量，不是整机起飞总重；训练侧应显式加入 empty_mass_kg/takeoff_mass_kg，而不是把 payload 当总重。")
    if source == "wemuav":
        actions.append("WEMUAV 当前 payload_kg 为 0 占位，不能用于学习载荷变化；应依赖无人机配置或外部机型参数补齐质量信息。")
    if payload_unique < 2:
        actions.append("该组载荷取值不足，无法从组内数据估计重量敏感度；需要跨任务或机型配置补充。")
    elif sensitivity_status != "reliable":
        actions.append(f"该组载荷-功率敏感度状态为 {sensitivity_status}，不能据此反推缺失重量，只能把常量偏差作为待解释现象。")
    elif np.isfinite(slope) and abs(slope) > 1e-9 and np.isfinite(equivalent_shift):
        if equivalent_shift < 0:
            actions.append(f"等效载荷偏移约 {equivalent_shift:.3f} kg，方向表现为模型像是少看了重量；可优先检查是否缺失空机/电池重量。")
        else:
            actions.append(f"等效载荷偏移约 +{equivalent_shift:.3f} kg，方向表现为模型像是看到了更大的重量；可检查残差修正、功率口径或载荷字段是否被重复解释。")
    if np.isfinite(bias):
        if bias > 0:
            actions.append("prediction_bias_w 为正，表示模型平均高估功率。")
        elif bias < 0:
            actions.append("prediction_bias_w 为负，表示模型平均低估功率。")
    return " ".join(actions)


def build_hypotheses(bias_table: pd.DataFrame, min_count: int, min_bias_share: float) -> pd.DataFrame:
    """筛选值得人工审计的常量偏差假设。"""

    if bias_table.empty:
        return bias_table
    frame = bias_table.copy()
    filtered = frame.loc[
        (frame["group_type"] == "source_phase")
        & (pd.to_numeric(frame["count"], errors="coerce") >= int(min_count))
        & (pd.to_numeric(frame["bias_share_of_rmse"], errors="coerce") >= float(min_bias_share))
    ].copy()
    if filtered.empty:
        return filtered
    filtered["training_side_hypothesis"] = filtered.apply(_hypothesis_action, axis=1)
    return filtered.sort_values(["bias_share_of_rmse", "mean_abs_target_error_pct"], ascending=[False, False])


def _json_records(frame: pd.DataFrame, limit: int) -> list[dict]:
    """把表格前若干行转换为 JSON 记录。"""

    return frame.head(limit).replace({np.nan: None}).to_dict(orient="records")


def main() -> None:
    """执行训练侧重量语义与常量偏差审计。"""

    args = parse_args()
    features_path = _resolve_path(args.features)
    benchmark_dir = _resolve_path(args.benchmark_dir)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(features_path)
    segment_errors = _read_segment_errors(benchmark_dir, args.variants)
    payload_semantics = build_payload_semantics(features)
    bias_table = build_bias_table(segment_errors, min_payload_slope_r2=args.min_payload_slope_r2)
    hypotheses = build_hypotheses(
        bias_table=bias_table,
        min_count=args.min_count,
        min_bias_share=args.min_bias_share,
    )

    payload_path = output_dir / "payload_semantics.csv"
    bias_path = output_dir / "constant_bias_by_group.csv"
    hypotheses_path = output_dir / "constant_bias_hypotheses.csv"
    payload_semantics.to_csv(payload_path, index=False)
    bias_table.to_csv(bias_path, index=False)
    hypotheses.to_csv(hypotheses_path, index=False)

    payload = {
        "features": str(features_path),
        "benchmark_dir": str(benchmark_dir),
        "variants": args.variants,
        "min_payload_slope_r2": args.min_payload_slope_r2,
        "row_counts": {
            "features": int(len(features.index)),
            "segment_errors": int(len(segment_errors.index)),
            "payload_semantics": int(len(payload_semantics.index)),
            "bias_table": int(len(bias_table.index)),
            "hypotheses": int(len(hypotheses.index)),
        },
        "top_payload_semantics": _json_records(payload_semantics, limit=20),
        "top_constant_bias_hypotheses": _json_records(hypotheses, limit=20),
        "outputs": {
            "payload_semantics": str(payload_path.resolve()),
            "constant_bias_by_group": str(bias_path.resolve()),
            "constant_bias_hypotheses": str(hypotheses_path.resolve()),
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
