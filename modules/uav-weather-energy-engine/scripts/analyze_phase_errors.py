# 分析规则阶段门控下的真实飞行回放误差，判断是否需要拆分专家模型。
"""分析阶段维度误差并输出专家模型候选。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_energy_engine.error_analysis import (
    build_flight_error_table,
    build_phase_error_table,
    build_segment_error_table,
    summarize_error_tables,
)
from uav_energy_engine.evaluate import save_summary
from uav_energy_engine.model import WeatherEnergyModel


EXPERT_CANDIDATE_COLUMNS = [
    "view",
    "phase",
    "count",
    "segment_share",
    "mean_abs_segment_energy_error_pct",
    "p95_abs_segment_energy_error_pct",
    "error_factor",
    "reason",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="分析阶段门控下的模型误差。")
    parser.add_argument(
        "--features",
        default="outputs/real_flight_replay_benchmark_phase_deployable_v2/segments_120s/segment_features_preflight.csv",
        help="部署口径特征 CSV",
    )
    parser.add_argument(
        "--model",
        default="outputs/real_flight_replay_benchmark_phase_deployable_v2/segments_120s/segment_wh_per_s/model.pkl",
        help="模型文件",
    )
    parser.add_argument("--target", default="segment_wh_per_s", help="预测目标列")
    parser.add_argument("--output-dir", default="outputs/phase_error_analysis_best", help="分析输出目录")
    parser.add_argument("--group-col", default="flight", help="测试切分和飞行聚合使用的分组列")
    parser.add_argument("--test-size", type=float, default=0.2, help="测试集比例")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    parser.add_argument("--battery-wh", type=float, default=130.0, help="可达性风险评估使用的电池容量 Wh")
    parser.add_argument("--active-threshold", type=float, default=0.2, help="阶段比例门控阈值")
    parser.add_argument("--expert-factor", type=float, default=1.5, help="阶段误差超过全局均值多少倍时列为专家候选")
    parser.add_argument("--min-segments", type=int, default=5, help="专家候选最小分段数")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _build_expert_candidates(
    phase_errors: pd.DataFrame,
    global_mean_abs_pct: float,
    min_segments: int,
    expert_factor: float,
) -> pd.DataFrame:
    """根据阶段误差生成专家模型候选表。"""

    if phase_errors.empty:
        return pd.DataFrame()

    rows = []
    frame = phase_errors.copy()
    frame["error_factor"] = pd.to_numeric(frame["mean_abs_segment_energy_error_pct"], errors="coerce") / float(global_mean_abs_pct)
    for _, row in frame.iterrows():
        count = int(row.get("count", 0))
        factor = float(row.get("error_factor", float("nan")))
        if count < min_segments or not pd.notna(factor) or factor < expert_factor:
            continue
        rows.append(
            {
                "view": row.get("view"),
                "phase": row.get("phase"),
                "count": count,
                "segment_share": row.get("segment_share"),
                "mean_abs_segment_energy_error_pct": row.get("mean_abs_segment_energy_error_pct"),
                "p95_abs_segment_energy_error_pct": row.get("p95_abs_segment_energy_error_pct"),
                "error_factor": factor,
                "reason": f"阶段平均误差达到全局均值的 {factor:.2f} 倍，且样本数 {count} >= {min_segments}",
            }
        )
    return pd.DataFrame(rows, columns=EXPERT_CANDIDATE_COLUMNS)


def main() -> None:
    """执行阶段误差分析。"""

    args = parse_args()
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model = WeatherEnergyModel.load(_resolve_path(args.model))
    segment_errors, segment_meta = build_segment_error_table(
        model=model,
        features_csv=_resolve_path(args.features),
        target=args.target,
        test_size=args.test_size,
        random_state=args.random_state,
        group_col=args.group_col,
    )
    flight_errors = build_flight_error_table(
        segment_errors=segment_errors,
        battery_wh=args.battery_wh,
        group_col=args.group_col,
    )
    phase_errors = build_phase_error_table(
        segment_errors=segment_errors,
        active_threshold=args.active_threshold,
    )
    summary = summarize_error_tables(
        segment_errors=segment_errors,
        flight_errors=flight_errors,
        segment_meta=segment_meta,
        battery_wh=args.battery_wh,
    )
    global_mean_abs_pct = float(summary["segment"]["mean_abs_target_error_pct"])
    expert_candidates = _build_expert_candidates(
        phase_errors=phase_errors,
        global_mean_abs_pct=global_mean_abs_pct,
        min_segments=args.min_segments,
        expert_factor=args.expert_factor,
    )

    segment_errors.to_csv(output_dir / "segment_errors.csv", index=False)
    flight_errors.to_csv(output_dir / "flight_errors.csv", index=False)
    phase_errors.to_csv(output_dir / "phase_errors.csv", index=False)
    expert_candidates.to_csv(output_dir / "expert_candidates.csv", index=False)

    payload = {
        **summary,
        "features_csv": str(_resolve_path(args.features)),
        "model_path": str(_resolve_path(args.model)),
        "phase_analysis": {
            "active_threshold": args.active_threshold,
            "expert_factor": args.expert_factor,
            "min_segments": args.min_segments,
            "global_mean_abs_segment_error_pct": global_mean_abs_pct,
            "phase_count": int(len(phase_errors.index)),
            "expert_candidate_count": int(len(expert_candidates.index)),
            "outputs": {
                "segment_errors": str((output_dir / "segment_errors.csv").resolve()),
                "flight_errors": str((output_dir / "flight_errors.csv").resolve()),
                "phase_errors": str((output_dir / "phase_errors.csv").resolve()),
                "expert_candidates": str((output_dir / "expert_candidates.csv").resolve()),
                "summary": str((output_dir / "summary.json").resolve()),
            },
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
