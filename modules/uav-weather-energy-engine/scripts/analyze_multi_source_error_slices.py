# 汇总多随机种子误差结果，按数据源、阶段、风速、高度、距离和时长定位高误差区域。
"""分析多来源能耗模型的误差切片。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd

from uav_energy_engine.evaluate import save_summary


CATEGORY_DIMENSIONS = [
    "source_dataset",
    "phase_label",
    "source_phase",
    "wind_speed_source",
    "wind_angle_source",
    "altitude_source",
]
NUMERIC_DIMENSIONS = [
    "wind_speed_mps",
    "headwind_mps",
    "crosswind_mps",
    "altitude_m",
    "distance_m",
    "duration_s",
    "planned_ground_speed_mps",
]
METRIC_COLUMNS = [
    "actual_target_value",
    "predicted_target_value",
    "target_error",
    "abs_target_error",
    "abs_target_error_pct",
    "actual_segment_energy_wh",
    "predicted_segment_energy_wh",
    "segment_energy_error_wh",
    "abs_segment_energy_error_wh",
    "abs_segment_energy_error_pct",
    "distance_m",
    "duration_s",
    "wind_speed_mps",
    "headwind_mps",
    "crosswind_mps",
    "altitude_m",
    "planned_ground_speed_mps",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="分析多随机种子误差切片。")
    parser.add_argument(
        "--benchmark-dir",
        default="outputs/multi_source_training/robustness_benchmark",
        help="多随机种子基准输出目录",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/multi_source_training/error_slice_analysis",
        help="误差切片分析输出目录",
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        default=["physical_source_flags__source_phase_joint"],
        help="要分析的变体名；传入 all 表示分析所有变体",
    )
    parser.add_argument("--bins", type=int, default=4, help="数值字段分桶数量")
    parser.add_argument("--min-count", type=int, default=10, help="列入问题切片的最小评估行数")
    parser.add_argument("--min-error-factor", type=float, default=1.15, help="问题切片误差超过全局均值的最小倍数")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _safe_float(value: object) -> float:
    """把数值转换为可 JSON 序列化的浮点数。"""

    if value is None:
        return float("nan")
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out


def _rmse(errors: pd.Series) -> float:
    """计算误差序列的均方根误差。"""

    values = pd.to_numeric(errors, errors="coerce").dropna().to_numpy(dtype=float)
    if values.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(np.square(values))))


def _pct(numerator: float, denominator: float) -> float:
    """安全计算百分比。"""

    if not np.isfinite(denominator) or abs(denominator) <= 1e-9:
        return float("nan")
    return float(numerator / denominator * 100.0)


def _parse_random_state(path: Path) -> int | None:
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


def _read_segment_errors(benchmark_dir: Path, variants: Iterable[str]) -> pd.DataFrame:
    """读取指定变体的全部分段误差表。"""

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
        if "source_dataset" in frame.columns and "phase_label" in frame.columns:
            frame["source_phase"] = (
                frame["source_dataset"].fillna("unknown").astype(str)
                + " / "
                + frame["phase_label"].fillna("unknown").astype(str)
            )
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"没有找到匹配的 segment_errors.csv: {benchmark_dir}")
    return pd.concat(frames, ignore_index=True)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    """读取数值列，缺失时返回空数值序列。"""

    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _unique_segment_count(frame: pd.DataFrame) -> int | None:
    """统计去重后的真实分段数量。"""

    keys = [column for column in ["flight", "segment_id"] if column in frame.columns]
    if not keys:
        return None
    return int(frame[keys].astype(str).drop_duplicates().shape[0])


def _metric_row(
    group: pd.DataFrame,
    *,
    variant: str,
    dimension: str,
    bucket: str,
    bucket_type: str,
    bucket_order: int,
    bucket_min: float = float("nan"),
    bucket_max: float = float("nan"),
) -> dict:
    """汇总一个误差切片。"""

    actual_target = _numeric(group, "actual_target_value")
    predicted_target = _numeric(group, "predicted_target_value")
    target_error = predicted_target - actual_target
    actual_energy = _numeric(group, "actual_segment_energy_wh")
    predicted_energy = _numeric(group, "predicted_segment_energy_wh")
    energy_error = predicted_energy - actual_energy
    actual_energy_sum = float(actual_energy.sum())
    predicted_energy_sum = float(predicted_energy.sum())
    energy_error_sum = predicted_energy_sum - actual_energy_sum
    abs_target_pct = _numeric(group, "abs_target_error_pct")
    abs_energy_pct = _numeric(group, "abs_segment_energy_error_pct")
    abs_energy_wh = _numeric(group, "abs_segment_energy_error_wh")
    speed_series = _numeric(group, "planned_ground_speed_mps")
    if speed_series.notna().sum() == 0:
        speed_series = _numeric(group, "speed_mps")

    return {
        "variant": variant,
        "dimension": dimension,
        "bucket": bucket,
        "bucket_type": bucket_type,
        "bucket_order": bucket_order,
        "bucket_min": bucket_min,
        "bucket_max": bucket_max,
        "count": int(len(group.index)),
        "unique_segment_count": _unique_segment_count(group),
        "seed_count": int(group["random_state"].nunique()) if "random_state" in group.columns else None,
        "flight_count": int(group["flight"].nunique()) if "flight" in group.columns else None,
        "target_bias": float(target_error.mean()),
        "target_mae": float(target_error.abs().mean()),
        "target_rmse": _rmse(target_error),
        "mean_abs_target_error_pct": float(abs_target_pct.mean()),
        "p90_abs_target_error_pct": float(abs_target_pct.quantile(0.90)),
        "p95_abs_target_error_pct": float(abs_target_pct.quantile(0.95)),
        "actual_energy_wh": actual_energy_sum,
        "predicted_energy_wh": predicted_energy_sum,
        "energy_error_wh": energy_error_sum,
        "energy_error_pct": _pct(energy_error_sum, actual_energy_sum),
        "mean_abs_segment_energy_error_wh": float(abs_energy_wh.mean()),
        "p90_abs_segment_energy_error_wh": float(abs_energy_wh.quantile(0.90)),
        "p95_abs_segment_energy_error_wh": float(abs_energy_wh.quantile(0.95)),
        "mean_abs_segment_energy_error_pct": float(abs_energy_pct.mean()),
        "p90_abs_segment_energy_error_pct": float(abs_energy_pct.quantile(0.90)),
        "p95_abs_segment_energy_error_pct": float(abs_energy_pct.quantile(0.95)),
        "underprediction_rate": float((energy_error < 0).mean()),
        "severe_underprediction_gt_10pct_rate": float((_numeric(group, "segment_energy_error_pct") < -10.0).mean()),
        "severe_underprediction_gt_25pct_rate": float((_numeric(group, "segment_energy_error_pct") < -25.0).mean()),
        "mean_distance_m": float(_numeric(group, "distance_m").mean()),
        "mean_duration_s": float(_numeric(group, "duration_s").mean()),
        "mean_planned_ground_speed_mps": float(speed_series.mean()),
        "mean_wind_speed_mps": float(_numeric(group, "wind_speed_mps").mean()),
        "mean_headwind_mps": float(_numeric(group, "headwind_mps").mean()),
        "mean_crosswind_mps": float(_numeric(group, "crosswind_mps").mean()),
        "mean_altitude_m": float(_numeric(group, "altitude_m").mean()),
    }


def _global_rows(frame: pd.DataFrame) -> list[dict]:
    """生成每个变体的全局误差行。"""

    rows = []
    for variant, group in frame.groupby("variant", sort=False):
        rows.append(
            _metric_row(
                group,
                variant=str(variant),
                dimension="global",
                bucket="all",
                bucket_type="global",
                bucket_order=0,
            )
        )
    return rows


def _category_rows(frame: pd.DataFrame, dimensions: Iterable[str]) -> list[dict]:
    """生成类别字段切片。"""

    rows = []
    for variant, variant_group in frame.groupby("variant", sort=False):
        for dimension in dimensions:
            if dimension not in variant_group.columns:
                continue
            values = variant_group[dimension].fillna("unknown").astype(str)
            for order, (bucket, group) in enumerate(variant_group.assign(_bucket=values).groupby("_bucket", sort=True)):
                rows.append(
                    _metric_row(
                        group,
                        variant=str(variant),
                        dimension=dimension,
                        bucket=str(bucket),
                        bucket_type="category",
                        bucket_order=order,
                    )
                )
    return rows


def _numeric_rows(frame: pd.DataFrame, dimensions: Iterable[str], bins: int) -> list[dict]:
    """生成数值字段分桶切片。"""

    rows = []
    for variant, variant_group in frame.groupby("variant", sort=False):
        for dimension in dimensions:
            if dimension not in variant_group.columns:
                continue
            values = pd.to_numeric(variant_group[dimension], errors="coerce")
            valid = variant_group.loc[values.notna()].copy()
            unique_count = int(values.nunique(dropna=True))
            if valid.empty or unique_count < 2:
                continue
            try:
                buckets = pd.qcut(
                    pd.to_numeric(valid[dimension], errors="coerce"),
                    q=min(bins, unique_count),
                    duplicates="drop",
                )
            except ValueError:
                continue
            valid = valid.assign(_bucket=buckets)
            categories = list(valid["_bucket"].cat.categories)
            for order, bucket in enumerate(categories):
                group = valid.loc[valid["_bucket"] == bucket]
                if group.empty:
                    continue
                bucket_values = pd.to_numeric(group[dimension], errors="coerce")
                rows.append(
                    _metric_row(
                        group,
                        variant=str(variant),
                        dimension=dimension,
                        bucket=str(bucket),
                        bucket_type="quantile",
                        bucket_order=order,
                        bucket_min=float(bucket_values.min()),
                        bucket_max=float(bucket_values.max()),
                    )
                )
    return rows


def _build_slice_table(frame: pd.DataFrame, bins: int) -> pd.DataFrame:
    """生成全部误差切片表。"""

    rows = []
    rows.extend(_global_rows(frame))
    rows.extend(_category_rows(frame, CATEGORY_DIMENSIONS))
    rows.extend(_numeric_rows(frame, NUMERIC_DIMENSIONS, bins))
    return pd.DataFrame(rows)


def _add_error_factors(slice_table: pd.DataFrame) -> pd.DataFrame:
    """为切片表加入相对全局误差倍数。"""

    if slice_table.empty:
        return slice_table

    global_errors = (
        slice_table.loc[slice_table["dimension"] == "global", ["variant", "mean_abs_target_error_pct"]]
        .rename(columns={"mean_abs_target_error_pct": "global_mean_abs_target_error_pct"})
        .copy()
    )
    frame = slice_table.merge(global_errors, on="variant", how="left")
    denominator = pd.to_numeric(frame["global_mean_abs_target_error_pct"], errors="coerce").replace(0, np.nan)
    frame["error_factor"] = pd.to_numeric(frame["mean_abs_target_error_pct"], errors="coerce") / denominator
    frame.loc[frame["dimension"] == "global", "error_factor"] = 1.0
    return frame


def _build_problem_slices(slice_table: pd.DataFrame, min_count: int, min_error_factor: float) -> pd.DataFrame:
    """筛选高误差且样本量足够的问题切片。"""

    if slice_table.empty:
        return slice_table

    frame = slice_table.copy()
    if "error_factor" not in frame.columns or "global_mean_abs_target_error_pct" not in frame.columns:
        frame = _add_error_factors(frame)
    frame = frame.loc[frame["dimension"] != "global"].copy()
    frame["priority_score"] = frame["error_factor"] * frame["count"].map(lambda value: math.log1p(float(value)))
    filtered = frame.loc[
        (pd.to_numeric(frame["count"], errors="coerce") >= int(min_count))
        & (pd.to_numeric(frame["error_factor"], errors="coerce") >= float(min_error_factor))
    ].copy()
    return filtered.sort_values(
        ["priority_score", "mean_abs_target_error_pct", "count"],
        ascending=[False, False, False],
    )


def _json_records(frame: pd.DataFrame, limit: int) -> list[dict]:
    """转换为 JSON 记录并清理不可序列化数值。"""

    records = []
    for row in frame.head(limit).to_dict(orient="records"):
        records.append(
            {
                key: (_safe_float(value) if isinstance(value, (float, np.floating, int, np.integer)) else value)
                for key, value in row.items()
            }
        )
    return records


def main() -> None:
    """执行误差切片分析。"""

    args = parse_args()
    benchmark_dir = _resolve_path(args.benchmark_dir)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    segment_errors = _read_segment_errors(benchmark_dir, args.variants)
    for column in METRIC_COLUMNS:
        if column in segment_errors.columns:
            segment_errors[column] = pd.to_numeric(segment_errors[column], errors="coerce")

    slice_table = _add_error_factors(_build_slice_table(segment_errors, bins=args.bins))
    problem_slices = _build_problem_slices(
        slice_table=slice_table,
        min_count=args.min_count,
        min_error_factor=args.min_error_factor,
    )

    segment_path = output_dir / "combined_segment_errors.csv"
    slice_path = output_dir / "slice_errors.csv"
    problem_path = output_dir / "problem_slices.csv"
    segment_errors.to_csv(segment_path, index=False)
    slice_table.to_csv(slice_path, index=False)
    problem_slices.to_csv(problem_path, index=False)

    payload = {
        "benchmark_dir": str(benchmark_dir),
        "output_dir": str(output_dir),
        "variants": args.variants,
        "bins": args.bins,
        "min_count": args.min_count,
        "min_error_factor": args.min_error_factor,
        "row_counts": {
            "segment_errors": int(len(segment_errors.index)),
            "slice_errors": int(len(slice_table.index)),
            "problem_slices": int(len(problem_slices.index)),
        },
        "global": _json_records(slice_table.loc[slice_table["dimension"] == "global"], limit=20),
        "top_problem_slices": _json_records(problem_slices, limit=20),
        "outputs": {
            "combined_segment_errors": str(segment_path.resolve()),
            "slice_errors": str(slice_path.resolve()),
            "problem_slices": str(problem_path.resolve()),
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
