# 中文说明：本文件运行多场景多随机种子的任务语义稳定性验证实验。
from __future__ import annotations

import csv
import json
from pathlib import Path

from .offloading import OffloadingEnv
from .scenarios import make_offloading_config_for_coverage
from .simulation import (
    TrainingResult,
    build_decision_trace_rows,
    build_policy_table_rows,
    evaluate_trained_q_learning,
    run_basic_strategy_suite,
)


CSVValue = float | int | str
CSVRow = dict[str, CSVValue]
SEMANTIC_FIELDS = ("task_urgency", "data_sensitivity", "area_risk")


def run_task_semantics_stability(
    *,
    scenario_names: tuple[str, ...],
    seeds: tuple[int, ...],
    slots: int,
    output_dir: Path,
) -> dict[str, str]:
    """运行多场景多 seed 验证，检查任务语义是否稳定影响卸载策略。"""

    if slots <= 0:
        raise ValueError("slots must be positive")
    if not scenario_names:
        raise ValueError("scenario_names must not be empty")
    if not seeds:
        raise ValueError("seeds must not be empty")

    output_dir.mkdir(parents=True, exist_ok=True)
    metric_rows: list[CSVRow] = []
    trace_trend_rows: list[CSVRow] = []
    greedy_trace_trend_rows: list[CSVRow] = []
    policy_trend_rows: list[CSVRow] = []

    for scenario_name in scenario_names:
        config = make_offloading_config_for_coverage(scenario_name)
        for seed in seeds:
            suite = run_basic_strategy_suite(config=config, slots=slots, seed=seed)
            greedy_metrics = evaluate_trained_q_learning(suite.q_learning, slots=slots, seed=seed)

            for strategy, metrics in suite.metrics_by_strategy.items():
                metric_rows.append(
                    {
                        "coverage_scenario": scenario_name,
                        "seed": seed,
                        "strategy": strategy,
                        **metrics.as_dict(),
                    }
                )
            metric_rows.append(
                {
                    "coverage_scenario": scenario_name,
                    "seed": seed,
                    "strategy": "q_learning_greedy",
                    **greedy_metrics.as_dict(),
                }
            )

            trace_rows = build_decision_trace_rows(suite.q_learning)
            greedy_trace_rows = _build_greedy_trace_rows(suite.q_learning, slots=slots, seed=seed)
            policy_rows = build_policy_table_rows(suite.q_learning)
            trace_trend_rows.extend(_build_trace_semantic_trends(scenario_name, seed, trace_rows))
            greedy_trace_trend_rows.extend(_build_trace_semantic_trends(scenario_name, seed, greedy_trace_rows))
            policy_trend_rows.extend(_build_policy_semantic_trends(scenario_name, seed, policy_rows))

    stability_rows = _build_stability_summary(trace_trend_rows, greedy_trace_trend_rows, policy_trend_rows)
    urgency_penalty_rows = _build_urgency_penalty_summary(trace_trend_rows, greedy_trace_trend_rows)
    notes = _build_stability_notes(stability_rows, urgency_penalty_rows)

    artifacts = {
        "task_semantics_metrics_csv": str(output_dir / "task_semantics_metrics.csv"),
        "task_semantics_metrics_json": str(output_dir / "task_semantics_metrics.json"),
        "task_semantics_trace_trends_csv": str(output_dir / "task_semantics_trace_trends.csv"),
        "task_semantics_trace_trends_json": str(output_dir / "task_semantics_trace_trends.json"),
        "task_semantics_greedy_trace_trends_csv": str(output_dir / "task_semantics_greedy_trace_trends.csv"),
        "task_semantics_greedy_trace_trends_json": str(output_dir / "task_semantics_greedy_trace_trends.json"),
        "task_semantics_policy_trends_csv": str(output_dir / "task_semantics_policy_trends.csv"),
        "task_semantics_policy_trends_json": str(output_dir / "task_semantics_policy_trends.json"),
        "task_semantics_stability_summary_csv": str(output_dir / "task_semantics_stability_summary.csv"),
        "task_semantics_stability_summary_json": str(output_dir / "task_semantics_stability_summary.json"),
        "task_urgency_penalty_summary_csv": str(output_dir / "task_urgency_penalty_summary.csv"),
        "task_urgency_penalty_summary_json": str(output_dir / "task_urgency_penalty_summary.json"),
        "task_semantics_stability_notes_json": str(output_dir / "task_semantics_stability_notes.json"),
    }
    _write_table(Path(artifacts["task_semantics_metrics_csv"]), Path(artifacts["task_semantics_metrics_json"]), metric_rows)
    _write_table(
        Path(artifacts["task_semantics_trace_trends_csv"]),
        Path(artifacts["task_semantics_trace_trends_json"]),
        trace_trend_rows,
    )
    _write_table(
        Path(artifacts["task_semantics_greedy_trace_trends_csv"]),
        Path(artifacts["task_semantics_greedy_trace_trends_json"]),
        greedy_trace_trend_rows,
    )
    _write_table(
        Path(artifacts["task_semantics_policy_trends_csv"]),
        Path(artifacts["task_semantics_policy_trends_json"]),
        policy_trend_rows,
    )
    _write_table(
        Path(artifacts["task_semantics_stability_summary_csv"]),
        Path(artifacts["task_semantics_stability_summary_json"]),
        stability_rows,
    )
    _write_table(
        Path(artifacts["task_urgency_penalty_summary_csv"]),
        Path(artifacts["task_urgency_penalty_summary_json"]),
        urgency_penalty_rows,
    )
    Path(artifacts["task_semantics_stability_notes_json"]).write_text(
        json.dumps(notes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return artifacts


def _build_greedy_trace_rows(result: TrainingResult, *, slots: int, seed: int) -> list[dict[str, CSVValue]]:
    env = OffloadingEnv(config=result.config, seed=seed)
    state = env.reset(seed=seed)
    rows: list[dict[str, CSVValue]] = []
    for slot in range(slots):
        state_index = env.encode_state(state)
        action_index = result.agent.select_action(state_index, explore=False)
        action = env.actions[action_index]
        step_result = env.step(state, action)
        rows.append(
            {
                "slot": slot,
                "queue": step_result.state.queue,
                "link": step_result.state.link,
                "battery": step_result.state.battery,
                "edge_load": step_result.state.edge_load,
                "cloud_load": step_result.state.cloud_load,
                "task_urgency": step_result.state.task_urgency,
                "data_sensitivity": step_result.state.data_sensitivity,
                "area_risk": step_result.state.area_risk,
                "executed_local_tasks": step_result.breakdown.executed_action.local_tasks,
                "executed_offload_tasks": step_result.breakdown.executed_action.offload_tasks,
                "executed_cloud_tasks": step_result.breakdown.executed_action.cloud_tasks,
                "reward": step_result.reward,
                "deadline_miss_penalty": step_result.breakdown.deadline_miss_penalty,
            }
        )
        state = step_result.next_state
    return rows


def _build_trace_semantic_trends(
    scenario_name: str,
    seed: int,
    rows: list[dict[str, CSVValue]],
) -> list[CSVRow]:
    trend_rows: list[CSVRow] = []
    for field in SEMANTIC_FIELDS:
        low_rows = [row for row in rows if row[field] == 0]
        high_rows = [row for row in rows if row[field] == 2]
        low_offload_ratio = _trace_offload_ratio(low_rows)
        high_offload_ratio = _trace_offload_ratio(high_rows)
        trend_rows.append(
            {
                "coverage_scenario": scenario_name,
                "seed": seed,
                "semantic_field": field,
                "low_level": 0,
                "high_level": 2,
                "low_slots": len(low_rows),
                "high_slots": len(high_rows),
                "low_offload_ratio": low_offload_ratio,
                "high_offload_ratio": high_offload_ratio,
                "offload_ratio_delta": high_offload_ratio - low_offload_ratio,
                "low_deadline_miss_rate": _deadline_miss_rate(low_rows),
                "high_deadline_miss_rate": _deadline_miss_rate(high_rows),
                "deadline_miss_rate_delta": _deadline_miss_rate(high_rows) - _deadline_miss_rate(low_rows),
                "low_average_deadline_miss_penalty": _mean(low_rows, "deadline_miss_penalty"),
                "high_average_deadline_miss_penalty": _mean(high_rows, "deadline_miss_penalty"),
                "average_deadline_miss_penalty_delta": _mean(high_rows, "deadline_miss_penalty")
                - _mean(low_rows, "deadline_miss_penalty"),
                "low_average_reward": _mean(low_rows, "reward"),
                "high_average_reward": _mean(high_rows, "reward"),
                "average_reward_delta": _mean(high_rows, "reward") - _mean(low_rows, "reward"),
            }
        )
    return trend_rows


def _build_policy_semantic_trends(
    scenario_name: str,
    seed: int,
    rows: list[dict[str, CSVValue]],
) -> list[CSVRow]:
    trend_rows: list[CSVRow] = []
    for field in SEMANTIC_FIELDS:
        low_rows = [row for row in rows if row[field] == 0]
        high_rows = [row for row in rows if row[field] == 2]
        low_average_offload_tasks = _mean_remote_tasks(low_rows)
        high_average_offload_tasks = _mean_remote_tasks(high_rows)
        low_offload_preferred = _offload_preferred_ratio(low_rows)
        high_offload_preferred = _offload_preferred_ratio(high_rows)
        trend_rows.append(
            {
                "coverage_scenario": scenario_name,
                "seed": seed,
                "semantic_field": field,
                "low_level": 0,
                "high_level": 2,
                "low_states": len(low_rows),
                "high_states": len(high_rows),
                "low_average_offload_tasks": low_average_offload_tasks,
                "high_average_offload_tasks": high_average_offload_tasks,
                "low_average_edge_tasks": _mean(low_rows, "offload_tasks"),
                "high_average_edge_tasks": _mean(high_rows, "offload_tasks"),
                "low_average_cloud_tasks": _mean(low_rows, "cloud_tasks"),
                "high_average_cloud_tasks": _mean(high_rows, "cloud_tasks"),
                "average_offload_tasks_delta": high_average_offload_tasks - low_average_offload_tasks,
                "low_offload_preferred_state_ratio": low_offload_preferred,
                "high_offload_preferred_state_ratio": high_offload_preferred,
                "offload_preferred_state_ratio_delta": high_offload_preferred - low_offload_preferred,
            }
        )
    return trend_rows


def _build_stability_summary(
    trace_rows: list[CSVRow],
    greedy_trace_rows: list[CSVRow],
    policy_rows: list[CSVRow],
) -> list[CSVRow]:
    summary_rows: list[CSVRow] = []
    summary_rows.extend(
        _summarize_delta_rows(
            rows=trace_rows,
            source="trace",
            delta_key="offload_ratio_delta",
        )
    )
    summary_rows.extend(
        _summarize_delta_rows(
            rows=greedy_trace_rows,
            source="greedy_trace",
            delta_key="offload_ratio_delta",
        )
    )
    summary_rows.extend(
        _summarize_delta_rows(
            rows=policy_rows,
            source="policy",
            delta_key="average_offload_tasks_delta",
        )
    )
    return summary_rows


def _build_urgency_penalty_summary(
    trace_rows: list[CSVRow],
    greedy_trace_rows: list[CSVRow],
) -> list[CSVRow]:
    summary_rows: list[CSVRow] = []
    for source, rows in (("trace", trace_rows), ("greedy_trace", greedy_trace_rows)):
        urgency_rows = [row for row in rows if row["semantic_field"] == "task_urgency"]
        scenario_names = sorted({str(row["coverage_scenario"]) for row in urgency_rows})
        for scenario_name in (*scenario_names, "all"):
            scenario_rows = (
                urgency_rows
                if scenario_name == "all"
                else [row for row in urgency_rows if row["coverage_scenario"] == scenario_name]
            )
            if not scenario_rows:
                continue
            penalty_deltas = [float(row["average_deadline_miss_penalty_delta"]) for row in scenario_rows]
            reward_deltas = [float(row["average_reward_delta"]) for row in scenario_rows]
            deadline_miss_rate_deltas = [float(row["deadline_miss_rate_delta"]) for row in scenario_rows]
            aligned_count = sum(
                1
                for penalty_delta, reward_delta in zip(penalty_deltas, reward_deltas, strict=True)
                if penalty_delta > 0.0 and reward_delta < 0.0
            )
            summary_rows.append(
                {
                    "coverage_scenario": scenario_name,
                    "source": source,
                    "semantic_field": "task_urgency",
                    "run_count": len(scenario_rows),
                    "aligned_count": aligned_count,
                    "penalty_alignment_ratio": aligned_count / len(scenario_rows),
                    "mean_deadline_miss_rate_delta": sum(deadline_miss_rate_deltas) / len(deadline_miss_rate_deltas),
                    "mean_deadline_miss_penalty_delta": sum(penalty_deltas) / len(penalty_deltas),
                    "mean_reward_delta": sum(reward_deltas) / len(reward_deltas),
                    "min_deadline_miss_penalty_delta": min(penalty_deltas),
                    "max_deadline_miss_penalty_delta": max(penalty_deltas),
                    "min_reward_delta": min(reward_deltas),
                    "max_reward_delta": max(reward_deltas),
                }
            )
    return summary_rows


def _summarize_delta_rows(rows: list[CSVRow], source: str, delta_key: str) -> list[CSVRow]:
    summary_rows: list[CSVRow] = []
    scenario_names = sorted({str(row["coverage_scenario"]) for row in rows})
    for scenario_name in (*scenario_names, "all"):
        scenario_rows = rows if scenario_name == "all" else [row for row in rows if row["coverage_scenario"] == scenario_name]
        for field in SEMANTIC_FIELDS:
            field_rows = [row for row in scenario_rows if row["semantic_field"] == field]
            if not field_rows:
                continue
            deltas = [float(row[delta_key]) for row in field_rows]
            stable_count = sum(1 for delta in deltas if delta < 0.0)
            summary_rows.append(
                {
                    "coverage_scenario": scenario_name,
                    "source": source,
                    "semantic_field": field,
                    "run_count": len(field_rows),
                    "stable_count": stable_count,
                    "stable_ratio": stable_count / len(field_rows),
                    "mean_delta": sum(deltas) / len(deltas),
                    "min_delta": min(deltas),
                    "max_delta": max(deltas),
                }
            )
    return summary_rows


def _build_stability_notes(summary_rows: list[CSVRow], urgency_penalty_rows: list[CSVRow]) -> dict[str, str]:
    notes = {
        "summary": "stable_ratio 表示高语义等级的卸载指标低于低等级的比例；越接近 1 越稳定。",
        "pass_rule": (
            "trace 包含 epsilon 探索，仅作训练过程参考；data_sensitivity 和 area_risk 建议看 "
            "greedy_trace 与 policy 的 offload stable_ratio，若 all 聚合下两者均 >= 0.8，"
            "可认为少卸载趋势较稳定。task_urgency 不强行要求少卸载，建议看 "
            "task_urgency_penalty_summary.csv 的 penalty_alignment_ratio；若 greedy_trace all >= 0.8，"
            "可认为 deadline 惩罚口径稳定。"
        ),
    }
    for field in SEMANTIC_FIELDS:
        trace = _find_summary_row(summary_rows, "all", "trace", field)
        greedy_trace = _find_summary_row(summary_rows, "all", "greedy_trace", field)
        policy = _find_summary_row(summary_rows, "all", "policy", field)
        if trace and greedy_trace and policy:
            notes[f"{field}_result"] = (
                f"trace stable_ratio={float(trace['stable_ratio']):.3f}, "
                f"greedy_trace stable_ratio={float(greedy_trace['stable_ratio']):.3f}, "
                f"policy stable_ratio={float(policy['stable_ratio']):.3f}, "
                f"trace mean_delta={float(trace['mean_delta']):.3f}, "
                f"greedy_trace mean_delta={float(greedy_trace['mean_delta']):.3f}, "
                f"policy mean_delta={float(policy['mean_delta']):.3f}。"
            )
    task_urgency_trace_rows = [
        row for row in summary_rows if row["coverage_scenario"] == "all" and row["source"] == "trace"
    ]
    if task_urgency_trace_rows:
        notes["deadline_metric_note"] = (
            "task_urgency 还应结合 task_semantics_trace_trends.csv 中的 "
            "deadline_miss_rate_delta 和 average_deadline_miss_penalty_delta 查看；"
            "高紧急度 deadline 更短，因此该指标用于衡量超时风险，而不是套用 stable_ratio。"
        )
    urgency_penalty = _find_urgency_penalty_row(urgency_penalty_rows, "all", "greedy_trace")
    if urgency_penalty:
        notes["task_urgency_penalty_result"] = (
            f"greedy_trace penalty_alignment_ratio={float(urgency_penalty['penalty_alignment_ratio']):.3f}, "
            f"mean_deadline_miss_penalty_delta={float(urgency_penalty['mean_deadline_miss_penalty_delta']):.3f}, "
            f"mean_reward_delta={float(urgency_penalty['mean_reward_delta']):.3f}。"
        )
    return notes


def _find_summary_row(rows: list[CSVRow], scenario: str, source: str, field: str) -> CSVRow | None:
    for row in rows:
        if row["coverage_scenario"] == scenario and row["source"] == source and row["semantic_field"] == field:
            return row
    return None


def _find_urgency_penalty_row(rows: list[CSVRow], scenario: str, source: str) -> CSVRow | None:
    for row in rows:
        if row["coverage_scenario"] == scenario and row["source"] == source:
            return row
    return None


def _trace_offload_ratio(rows: list[dict[str, CSVValue]]) -> float:
    processed = sum(
        int(row["executed_local_tasks"])
        + int(row["executed_offload_tasks"])
        + int(row.get("executed_cloud_tasks", 0))
        for row in rows
    )
    offloaded = sum(int(row["executed_offload_tasks"]) + int(row.get("executed_cloud_tasks", 0)) for row in rows)
    return offloaded / processed if processed else 0.0


def _deadline_miss_rate(rows: list[dict[str, CSVValue]]) -> float:
    if not rows:
        return 0.0
    misses = sum(1 for row in rows if float(row.get("deadline_miss_penalty", 0.0)) > 0.0)
    return misses / len(rows)


def _offload_preferred_ratio(rows: list[dict[str, CSVValue]]) -> float:
    if not rows:
        return 0.0
    offload_preferred = sum(
        1
        for row in rows
        if int(row["offload_tasks"]) + int(row.get("cloud_tasks", 0)) > int(row["local_tasks"])
    )
    return offload_preferred / len(rows)


def _mean_remote_tasks(rows: list[dict[str, CSVValue]]) -> float:
    if not rows:
        return 0.0
    return sum(float(row["offload_tasks"]) + float(row.get("cloud_tasks", 0)) for row in rows) / len(rows)


def _mean(rows: list[dict[str, CSVValue]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(float(row[field]) for row in rows) / len(rows)


def _write_table(csv_path: Path, json_path: Path, rows: list[CSVRow]) -> None:
    if not rows:
        raise ValueError(f"rows must not be empty for {csv_path}")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
