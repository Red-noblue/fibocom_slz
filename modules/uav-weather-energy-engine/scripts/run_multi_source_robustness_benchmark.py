# 多随机种子验证多来源能耗模型的特征组和残差修正策略是否稳定。
"""运行多来源能耗模型稳健性基准。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[0]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (SCRIPT_DIR, VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd

import run_multi_source_error_benchmark as benchmark
from uav_energy_engine.evaluate import save_summary
from uav_energy_engine.model import _prepare_training_frame
from uav_energy_engine.target_modes import infer_target_mode


DEFAULT_RANDOM_STATES = [7, 13, 21, 42, 84]
DEFAULT_METRICS = [
    "segment_rmse",
    "segment_mae",
    "segment_r2",
    "segment_mean_abs_target_error_pct",
    "segment_mean_abs_energy_error_wh",
    "segment_mean_abs_energy_error_pct",
    "flight_mean_abs_energy_error_wh",
    "flight_mean_abs_energy_error_pct",
    "range_mean_abs_error_pct",
    "source_m100_target_rmse",
    "source_wemuav_target_rmse",
]
IMPROVEMENT_METRICS = [
    "segment_rmse",
    "segment_mae",
    "segment_mean_abs_target_error_pct",
    "segment_mean_abs_energy_error_wh",
    "segment_mean_abs_energy_error_pct",
    "flight_mean_abs_energy_error_wh",
    "flight_mean_abs_energy_error_pct",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="运行多来源能耗模型稳健性基准。")
    parser.add_argument(
        "--features",
        default="outputs/multi_source_training/combined_power_preflight_weather_complete.csv",
        help="多来源训练表 CSV",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/multi_source_training/robustness_benchmark",
        help="输出目录",
    )
    parser.add_argument("--target", default="mean_power_w", help="训练目标列")
    parser.add_argument("--method", default="gradient_boosting", help="训练方法")
    parser.add_argument("--group-col", default="flight", help="训练/测试分组列")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    parser.add_argument(
        "--random-states",
        nargs="+",
        type=int,
        default=DEFAULT_RANDOM_STATES,
        help="重复评估使用的随机种子列表",
    )
    parser.add_argument("--battery-wh", type=float, default=130.0, help="风险评估使用的电池容量 Wh")
    parser.add_argument("--min-group-rows", type=int, default=5, help="残差修正中单组最小行数")
    parser.add_argument("--min-expert-rows", type=int, default=20, help="源域专家模型单源最小训练行数")
    parser.add_argument("--shrinkage-rows", type=float, default=20.0, help="残差修正向全局偏差收缩的强度")
    parser.add_argument(
        "--sample-weight-policies",
        nargs="+",
        default=["none"],
        choices=benchmark.SAMPLE_WEIGHT_POLICIES,
        help="要比较的训练样本权重策略",
    )
    parser.add_argument(
        "--feature-variants",
        nargs="+",
        default=["physical_source_flags", "physical_source_flags_pruned"],
        choices=sorted(benchmark.FEATURE_VARIANTS),
        help="要比较的特征组",
    )
    parser.add_argument(
        "--corrections",
        nargs="+",
        default=["source_phase_joint"],
        choices=sorted(benchmark.CORRECTION_VARIANTS),
        help="要比较的残差修正策略",
    )
    parser.add_argument(
        "--baseline-variant",
        default="physical_source_flags__source_phase_joint",
        help="用于计算相对改进的基线变体名",
    )
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _make_benchmark_args(args: argparse.Namespace, random_state: int, sample_weight_policy: str) -> SimpleNamespace:
    """构造复用单次基准函数所需的参数对象。"""

    return SimpleNamespace(
        target=args.target,
        method=args.method,
        random_state=random_state,
        battery_wh=args.battery_wh,
        min_group_rows=args.min_group_rows,
        min_expert_rows=args.min_expert_rows,
        shrinkage_rows=args.shrinkage_rows,
        sample_weight_policy=sample_weight_policy,
    )


def _ordered_unique(values: Iterable[int]) -> list[int]:
    """按输入顺序去重随机种子。"""

    seen = set()
    ordered = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _feature_columns(input_path: Path, cleaned: pd.DataFrame, target: str, feature_variant: str) -> list[str]:
    """根据特征组名称解析实际可用特征列。"""

    return benchmark._feature_columns_for_variant(input_path, target, cleaned, feature_variant)


def _run_seed(
    *,
    cleaned: pd.DataFrame,
    input_path: Path,
    output_dir: Path,
    args: argparse.Namespace,
    random_state: int,
) -> list[dict]:
    """运行单个随机种子的全部变体。"""

    seed_dir = output_dir / f"seed_{random_state:03d}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    train_frame, test_frame, split_meta = benchmark._split_frame(
        frame=cleaned,
        group_col=args.group_col,
        test_size=args.test_size,
        random_state=random_state,
    )
    train_frame.to_csv(seed_dir / "train_frame.csv", index=False)
    test_frame.to_csv(seed_dir / "test_frame.csv", index=False)

    rows = []
    for feature_variant in args.feature_variants:
        feature_cols = _feature_columns(input_path, cleaned, args.target, feature_variant)
        train_subset = train_frame.dropna(subset=feature_cols + [args.target]).copy()
        test_subset = test_frame.dropna(subset=feature_cols + [args.target]).copy()
        if train_subset.empty or test_subset.empty:
            continue
        for sample_weight_policy in args.sample_weight_policies:
            run_args = _make_benchmark_args(args, random_state, sample_weight_policy)
            for correction_name in args.corrections:
                row = benchmark._run_variant(
                    cleaned=cleaned,
                    feature_cols=feature_cols,
                    feature_variant=feature_variant,
                    correction_name=correction_name,
                    args=run_args,
                    output_dir=seed_dir,
                    split_meta={**split_meta, "random_state": random_state},
                    train_frame=train_subset,
                    test_frame=test_subset,
                )
                row["random_state"] = random_state
                row["split_strategy"] = split_meta.get("split_strategy")
                row["seed_output_dir"] = str(seed_dir.resolve())
                rows.append(row)
    return rows


def _add_baseline_deltas(frame: pd.DataFrame, baseline_variant: str) -> pd.DataFrame:
    """加入相对基线的误差下降量和下降比例。"""

    if frame.empty or "variant" not in frame.columns:
        return frame

    baseline = frame.loc[frame["variant"] == baseline_variant, ["random_state", *IMPROVEMENT_METRICS]].copy()
    if baseline.empty:
        return frame

    baseline = baseline.rename(columns={metric: f"baseline_{metric}" for metric in IMPROVEMENT_METRICS})
    merged = frame.merge(baseline, on="random_state", how="left")
    for metric in IMPROVEMENT_METRICS:
        baseline_col = f"baseline_{metric}"
        delta_col = f"delta_vs_baseline_{metric}"
        improvement_col = f"improvement_vs_baseline_{metric}_pct"
        merged[delta_col] = pd.to_numeric(merged[baseline_col], errors="coerce") - pd.to_numeric(
            merged[metric],
            errors="coerce",
        )
        denominator = pd.to_numeric(merged[baseline_col], errors="coerce").replace(0, np.nan)
        merged[improvement_col] = merged[delta_col] / denominator * 100.0
    return merged


def _summarize_by_variant(frame: pd.DataFrame) -> pd.DataFrame:
    """按变体汇总多随机种子的均值、波动和胜率。"""

    if frame.empty:
        return frame

    summary_rows = []
    group_cols = ["variant", "feature_variant", "correction", "sample_weight_policy"]
    for keys, group in frame.groupby(group_cols, sort=False):
        row = dict(zip(group_cols, keys))
        row["seed_count"] = int(group["random_state"].nunique())
        row["feature_count"] = int(pd.to_numeric(group["feature_count"], errors="coerce").median())
        for metric in DEFAULT_METRICS:
            if metric not in group.columns:
                continue
            values = pd.to_numeric(group[metric], errors="coerce")
            row[f"{metric}_mean"] = float(values.mean())
            row[f"{metric}_std"] = float(values.std(ddof=0))
            row[f"{metric}_min"] = float(values.min())
            row[f"{metric}_max"] = float(values.max())
        for metric in IMPROVEMENT_METRICS:
            delta_col = f"delta_vs_baseline_{metric}"
            improvement_col = f"improvement_vs_baseline_{metric}_pct"
            if delta_col not in group.columns:
                continue
            deltas = pd.to_numeric(group[delta_col], errors="coerce")
            improvements = pd.to_numeric(group[improvement_col], errors="coerce")
            row[f"{delta_col}_mean"] = float(deltas.mean())
            row[f"{delta_col}_std"] = float(deltas.std(ddof=0))
            row[f"{improvement_col}_mean"] = float(improvements.mean())
            row[f"{metric}_win_rate"] = float((deltas > 0).mean())
        summary_rows.append(row)
    return pd.DataFrame(summary_rows)


def main() -> None:
    """执行多随机种子稳健性基准。"""

    args = parse_args()
    random_states = _ordered_unique(args.random_states)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = _resolve_path(args.features)

    all_requested_features = sorted(
        {
            feature
            for feature_variant in args.feature_variants
            for feature in benchmark.FEATURE_VARIANTS[feature_variant]
        }
    )
    cleaned, _ = _prepare_training_frame(input_path, [args.target], all_requested_features)
    cleaned = benchmark._with_auxiliary_strategy_columns(cleaned)

    rows = []
    for random_state in random_states:
        rows.extend(
            _run_seed(
                cleaned=cleaned,
                input_path=input_path,
                output_dir=output_dir,
                args=args,
                random_state=random_state,
            )
        )

    by_seed = _add_baseline_deltas(pd.DataFrame(rows), args.baseline_variant)
    by_seed_path = output_dir / "by_seed.csv"
    by_seed.to_csv(by_seed_path, index=False)

    summary = _summarize_by_variant(by_seed)
    summary_path = output_dir / "summary.csv"
    summary.to_csv(summary_path, index=False)

    best_by_rmse = summary.sort_values("segment_rmse_mean").iloc[0].to_dict() if not summary.empty else None
    best_by_flight_error = (
        summary.sort_values("flight_mean_abs_energy_error_pct_mean").iloc[0].to_dict()
        if not summary.empty and "flight_mean_abs_energy_error_pct_mean" in summary.columns
        else None
    )
    payload = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "target": args.target,
        "target_mode": infer_target_mode(args.target),
        "method": args.method,
        "random_states": random_states,
        "feature_variants": args.feature_variants,
        "corrections": args.corrections,
        "sample_weight_policies": args.sample_weight_policies,
        "baseline_variant": args.baseline_variant,
        "row_counts": {
            "cleaned": int(len(cleaned.index)),
            "by_seed": int(len(by_seed.index)),
            "summary": int(len(summary.index)),
        },
        "best_by_segment_rmse_mean": best_by_rmse,
        "best_by_flight_mean_abs_energy_error_pct_mean": best_by_flight_error,
        "outputs": {
            "by_seed": str(by_seed_path.resolve()),
            "summary_csv": str(summary_path.resolve()),
            "summary_json": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
