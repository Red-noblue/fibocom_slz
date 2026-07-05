# 中文说明：本文件分析端-边-云三层卸载实验，输出场景和任务语义专项对比。
from __future__ import annotations

import csv
import json
from pathlib import Path

from .offloading import OffloadingEnv
from .scenarios import make_offloading_config_for_coverage
from .simulation import (
    EpisodeMetrics,
    TrainingResult,
    build_decision_trace_rows,
    build_policy_table_rows,
    evaluate_trained_q_learning,
    run_basic_strategy_suite,
)


CSVValue = float | int | str
CSVRow = dict[str, CSVValue]
SEMANTIC_FIELDS = ("data_sensitivity", "area_risk")


def analyze_three_tier_sweep(input_dir: Path, output_dir: Path | None = None) -> dict[str, str]:
    """分析 run-scenarios 输出，检查三层卸载的场景与语义趋势。"""

    output_dir = output_dir or input_dir / "three_tier_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows = _read_csv(input_dir / "scenario_strategy_metrics.csv")
    scenario_names = sorted({row["coverage_scenario"] for row in metrics_rows})
    scenario_cloud_rows = _build_scenario_cloud_rows(metrics_rows)
    trace_trend_rows: list[CSVRow] = []
    policy_trend_rows: list[CSVRow] = []

    for scenario_name in scenario_names:
        trace_rows = _read_csv(input_dir / scenario_name / "decision_trace.csv")
        policy_rows = _read_csv(input_dir / scenario_name / "policy_table.csv")
        trace_trend_rows.extend(_build_trace_semantic_cloud_rows(scenario_name, trace_rows))
        policy_trend_rows.extend(_build_policy_semantic_cloud_rows(scenario_name, policy_rows))

    hypothesis_rows = _build_hypothesis_rows(scenario_cloud_rows, trace_trend_rows, policy_trend_rows)
    notes = _build_notes(hypothesis_rows)

    artifacts = {
        "three_tier_scenario_cloud_summary_csv": str(output_dir / "three_tier_scenario_cloud_summary.csv"),
        "three_tier_scenario_cloud_summary_json": str(output_dir / "three_tier_scenario_cloud_summary.json"),
        "three_tier_trace_semantic_cloud_trends_csv": str(
            output_dir / "three_tier_trace_semantic_cloud_trends.csv"
        ),
        "three_tier_trace_semantic_cloud_trends_json": str(
            output_dir / "three_tier_trace_semantic_cloud_trends.json"
        ),
        "three_tier_policy_semantic_cloud_trends_csv": str(
            output_dir / "three_tier_policy_semantic_cloud_trends.csv"
        ),
        "three_tier_policy_semantic_cloud_trends_json": str(
            output_dir / "three_tier_policy_semantic_cloud_trends.json"
        ),
        "three_tier_hypothesis_checks_csv": str(output_dir / "three_tier_hypothesis_checks.csv"),
        "three_tier_hypothesis_checks_json": str(output_dir / "three_tier_hypothesis_checks.json"),
        "three_tier_notes_json": str(output_dir / "three_tier_notes.json"),
    }
    _write_table(
        Path(artifacts["three_tier_scenario_cloud_summary_csv"]),
        Path(artifacts["three_tier_scenario_cloud_summary_json"]),
        scenario_cloud_rows,
    )
    _write_table(
        Path(artifacts["three_tier_trace_semantic_cloud_trends_csv"]),
        Path(artifacts["three_tier_trace_semantic_cloud_trends_json"]),
        trace_trend_rows,
    )
    _write_table(
        Path(artifacts["three_tier_policy_semantic_cloud_trends_csv"]),
        Path(artifacts["three_tier_policy_semantic_cloud_trends_json"]),
        policy_trend_rows,
    )
    _write_table(
        Path(artifacts["three_tier_hypothesis_checks_csv"]),
        Path(artifacts["three_tier_hypothesis_checks_json"]),
        hypothesis_rows,
    )
    Path(artifacts["three_tier_notes_json"]).write_text(
        json.dumps(notes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return artifacts


def validate_three_tier_stability(
    *,
    scenario_names: tuple[str, ...],
    seeds: tuple[int, ...],
    slots: int,
    output_dir: Path,
) -> dict[str, str]:
    """运行多 seed 三层卸载验证，检查场景和语义趋势是否稳定。"""

    if slots <= 0:
        raise ValueError("slots must be positive")
    if not scenario_names:
        raise ValueError("scenario_names must not be empty")
    if not seeds:
        raise ValueError("seeds must not be empty")

    output_dir.mkdir(parents=True, exist_ok=True)
    scenario_metric_rows: list[CSVRow] = []
    trace_trend_rows: list[CSVRow] = []
    greedy_trace_trend_rows: list[CSVRow] = []
    policy_trend_rows: list[CSVRow] = []

    for seed in seeds:
        for scenario_name in scenario_names:
            config = make_offloading_config_for_coverage(scenario_name)
            suite = run_basic_strategy_suite(config=config, slots=slots, seed=seed)
            greedy_metrics = evaluate_trained_q_learning(suite.q_learning, slots=slots, seed=seed)
            scenario_metric_rows.append(
                _build_seed_scenario_metric_row(
                    seed=seed,
                    scenario_name=scenario_name,
                    metric_source="trace",
                    metrics=suite.q_learning.metrics,
                )
            )
            scenario_metric_rows.append(
                _build_seed_scenario_metric_row(
                    seed=seed,
                    scenario_name=scenario_name,
                    metric_source="greedy_eval",
                    metrics=greedy_metrics,
                )
            )

            trace_rows = _stringify_rows(build_decision_trace_rows(suite.q_learning))
            greedy_trace_rows = _stringify_rows(_build_greedy_trace_rows(suite.q_learning, slots=slots, seed=seed))
            policy_rows = _stringify_rows(build_policy_table_rows(suite.q_learning))
            trace_trend_rows.extend(
                {"seed": seed, **row} for row in _build_trace_semantic_cloud_rows(scenario_name, trace_rows)
            )
            greedy_trace_trend_rows.extend(
                {"seed": seed, **row}
                for row in _build_trace_semantic_cloud_rows(scenario_name, greedy_trace_rows)
            )
            policy_trend_rows.extend(
                {"seed": seed, **row} for row in _build_policy_semantic_cloud_rows(scenario_name, policy_rows)
            )

    stability_rows = _build_stability_summary(
        scenario_metric_rows,
        trace_trend_rows,
        greedy_trace_trend_rows,
        policy_trend_rows,
    )
    notes = _build_stability_notes(stability_rows)

    artifacts = {
        "three_tier_seed_scenario_metrics_csv": str(output_dir / "three_tier_seed_scenario_metrics.csv"),
        "three_tier_seed_scenario_metrics_json": str(output_dir / "three_tier_seed_scenario_metrics.json"),
        "three_tier_trace_semantic_cloud_trends_csv": str(
            output_dir / "three_tier_trace_semantic_cloud_trends.csv"
        ),
        "three_tier_trace_semantic_cloud_trends_json": str(
            output_dir / "three_tier_trace_semantic_cloud_trends.json"
        ),
        "three_tier_greedy_trace_semantic_cloud_trends_csv": str(
            output_dir / "three_tier_greedy_trace_semantic_cloud_trends.csv"
        ),
        "three_tier_greedy_trace_semantic_cloud_trends_json": str(
            output_dir / "three_tier_greedy_trace_semantic_cloud_trends.json"
        ),
        "three_tier_policy_semantic_cloud_trends_csv": str(
            output_dir / "three_tier_policy_semantic_cloud_trends.csv"
        ),
        "three_tier_policy_semantic_cloud_trends_json": str(
            output_dir / "three_tier_policy_semantic_cloud_trends.json"
        ),
        "three_tier_stability_summary_csv": str(output_dir / "three_tier_stability_summary.csv"),
        "three_tier_stability_summary_json": str(output_dir / "three_tier_stability_summary.json"),
        "three_tier_stability_notes_json": str(output_dir / "three_tier_stability_notes.json"),
    }
    _write_table(
        Path(artifacts["three_tier_seed_scenario_metrics_csv"]),
        Path(artifacts["three_tier_seed_scenario_metrics_json"]),
        scenario_metric_rows,
    )
    _write_table(
        Path(artifacts["three_tier_trace_semantic_cloud_trends_csv"]),
        Path(artifacts["three_tier_trace_semantic_cloud_trends_json"]),
        trace_trend_rows,
    )
    _write_table(
        Path(artifacts["three_tier_greedy_trace_semantic_cloud_trends_csv"]),
        Path(artifacts["three_tier_greedy_trace_semantic_cloud_trends_json"]),
        greedy_trace_trend_rows,
    )
    _write_table(
        Path(artifacts["three_tier_policy_semantic_cloud_trends_csv"]),
        Path(artifacts["three_tier_policy_semantic_cloud_trends_json"]),
        policy_trend_rows,
    )
    _write_table(
        Path(artifacts["three_tier_stability_summary_csv"]),
        Path(artifacts["three_tier_stability_summary_json"]),
        stability_rows,
    )
    Path(artifacts["three_tier_stability_notes_json"]).write_text(
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
            }
        )
        state = step_result.next_state
    return rows


def _build_seed_scenario_metric_row(
    *,
    seed: int,
    scenario_name: str,
    metric_source: str,
    metrics: EpisodeMetrics,
) -> CSVRow:
    cloud_share = metrics.cloud_offload_ratio / metrics.offload_ratio if metrics.offload_ratio else 0.0
    return {
        "seed": seed,
        "coverage_scenario": scenario_name,
        "metric_source": metric_source,
        "average_reward": metrics.average_reward,
        "average_delay": metrics.average_delay,
        "average_energy": metrics.average_energy,
        "average_queue": metrics.average_queue,
        "processed_tasks": metrics.processed_tasks,
        "offload_ratio": metrics.offload_ratio,
        "edge_offload_ratio": metrics.edge_offload_ratio,
        "cloud_offload_ratio": metrics.cloud_offload_ratio,
        "cloud_share_of_remote": cloud_share,
        "cloud_minus_edge_ratio": metrics.cloud_offload_ratio - metrics.edge_offload_ratio,
    }


def _build_scenario_cloud_rows(metrics_rows: list[dict[str, str]]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    qlearning_rows = [row for row in metrics_rows if row["strategy"] == "q_learning"]
    for row in sorted(qlearning_rows, key=lambda item: item["coverage_scenario"]):
        offload_ratio = _to_float(row["offload_ratio"])
        edge_ratio = _to_float(row.get("edge_offload_ratio", row["offload_ratio"]))
        cloud_ratio = _to_float(row.get("cloud_offload_ratio", "0"))
        rows.append(
            {
                "coverage_scenario": row["coverage_scenario"],
                "average_reward": _to_float(row["average_reward"]),
                "average_delay": _to_float(row["average_delay"]),
                "average_energy": _to_float(row["average_energy"]),
                "average_queue": _to_float(row["average_queue"]),
                "processed_tasks": _to_int(row["processed_tasks"]),
                "offload_ratio": offload_ratio,
                "edge_offload_ratio": edge_ratio,
                "cloud_offload_ratio": cloud_ratio,
                "cloud_share_of_remote": cloud_ratio / offload_ratio if offload_ratio else 0.0,
                "cloud_minus_edge_ratio": cloud_ratio - edge_ratio,
            }
        )
    return rows


def _build_trace_semantic_cloud_rows(scenario_name: str, rows: list[dict[str, str]]) -> list[CSVRow]:
    trend_rows: list[CSVRow] = []
    for field in SEMANTIC_FIELDS:
        low_rows = [row for row in rows if row[field] == "0"]
        high_rows = [row for row in rows if row[field] == "2"]
        low = _trace_remote_metrics(low_rows)
        high = _trace_remote_metrics(high_rows)
        trend_rows.append(
            {
                "coverage_scenario": scenario_name,
                "semantic_field": field,
                "low_level": 0,
                "high_level": 2,
                "low_slots": len(low_rows),
                "high_slots": len(high_rows),
                "low_offload_ratio": low["offload_ratio"],
                "high_offload_ratio": high["offload_ratio"],
                "offload_ratio_delta": high["offload_ratio"] - low["offload_ratio"],
                "low_edge_offload_ratio": low["edge_offload_ratio"],
                "high_edge_offload_ratio": high["edge_offload_ratio"],
                "edge_offload_ratio_delta": high["edge_offload_ratio"] - low["edge_offload_ratio"],
                "low_cloud_offload_ratio": low["cloud_offload_ratio"],
                "high_cloud_offload_ratio": high["cloud_offload_ratio"],
                "cloud_offload_ratio_delta": high["cloud_offload_ratio"] - low["cloud_offload_ratio"],
                "low_average_reward": _mean(low_rows, "reward"),
                "high_average_reward": _mean(high_rows, "reward"),
                "average_reward_delta": _mean(high_rows, "reward") - _mean(low_rows, "reward"),
            }
        )
    return trend_rows


def _build_policy_semantic_cloud_rows(scenario_name: str, rows: list[dict[str, str]]) -> list[CSVRow]:
    trend_rows: list[CSVRow] = []
    for field in SEMANTIC_FIELDS:
        low_rows = [row for row in rows if row[field] == "0"]
        high_rows = [row for row in rows if row[field] == "2"]
        low_edge_tasks = _mean(low_rows, "offload_tasks")
        high_edge_tasks = _mean(high_rows, "offload_tasks")
        low_cloud_tasks = _mean(low_rows, "cloud_tasks")
        high_cloud_tasks = _mean(high_rows, "cloud_tasks")
        low_remote_tasks = low_edge_tasks + low_cloud_tasks
        high_remote_tasks = high_edge_tasks + high_cloud_tasks
        trend_rows.append(
            {
                "coverage_scenario": scenario_name,
                "semantic_field": field,
                "low_level": 0,
                "high_level": 2,
                "low_states": len(low_rows),
                "high_states": len(high_rows),
                "low_average_remote_tasks": low_remote_tasks,
                "high_average_remote_tasks": high_remote_tasks,
                "average_remote_tasks_delta": high_remote_tasks - low_remote_tasks,
                "low_average_edge_tasks": low_edge_tasks,
                "high_average_edge_tasks": high_edge_tasks,
                "average_edge_tasks_delta": high_edge_tasks - low_edge_tasks,
                "low_average_cloud_tasks": low_cloud_tasks,
                "high_average_cloud_tasks": high_cloud_tasks,
                "average_cloud_tasks_delta": high_cloud_tasks - low_cloud_tasks,
                "low_cloud_preferred_state_ratio": _cloud_preferred_ratio(low_rows),
                "high_cloud_preferred_state_ratio": _cloud_preferred_ratio(high_rows),
                "cloud_preferred_state_ratio_delta": _cloud_preferred_ratio(high_rows)
                - _cloud_preferred_ratio(low_rows),
            }
        )
    return trend_rows


def _build_hypothesis_rows(
    scenario_rows: list[CSVRow],
    trace_rows: list[CSVRow],
    policy_rows: list[CSVRow],
) -> list[CSVRow]:
    rows: list[CSVRow] = []
    by_scenario = {str(row["coverage_scenario"]): row for row in scenario_rows}
    weak = by_scenario.get("weak_coverage")
    congested = by_scenario.get("congested_edge")
    balanced = by_scenario.get("balanced")

    if weak:
        other_cloud_values = [
            float(row["cloud_offload_ratio"])
            for row in scenario_rows
            if row["coverage_scenario"] != "weak_coverage"
        ]
        other_mean = sum(other_cloud_values) / len(other_cloud_values) if other_cloud_values else 0.0
        weak_cloud = float(weak["cloud_offload_ratio"])
        rows.append(
            {
                "hypothesis": "weak_coverage_少云",
                "source": "scenario_metrics",
                "semantic_field": "",
                "passed": int(weak_cloud < other_mean),
                "primary_metric": weak_cloud,
                "threshold": other_mean,
                "detail": f"weak_coverage cloud_offload_ratio={weak_cloud:.3f}，其他场景均值={other_mean:.3f}。",
            }
        )

    if congested and balanced:
        congested_cloud = float(congested["cloud_offload_ratio"])
        balanced_cloud = float(balanced["cloud_offload_ratio"])
        congested_share = float(congested["cloud_share_of_remote"])
        rows.append(
            {
                "hypothesis": "congested_edge_转云",
                "source": "scenario_metrics",
                "semantic_field": "",
                "passed": int(congested_cloud > balanced_cloud and congested_share >= 0.45),
                "primary_metric": congested_cloud,
                "threshold": balanced_cloud,
                "detail": (
                    f"congested_edge cloud_offload_ratio={congested_cloud:.3f}，"
                    f"balanced={balanced_cloud:.3f}，云端占远端卸载={congested_share:.3f}。"
                ),
            }
        )

    rows.extend(_build_semantic_hypothesis_rows(trace_rows, "trace", "cloud_offload_ratio_delta"))
    rows.extend(_build_semantic_hypothesis_rows(policy_rows, "policy", "average_cloud_tasks_delta"))
    return rows


def _build_stability_summary(
    scenario_rows: list[CSVRow],
    trace_rows: list[CSVRow],
    greedy_trace_rows: list[CSVRow],
    policy_rows: list[CSVRow],
) -> list[CSVRow]:
    summary_rows: list[CSVRow] = []
    for source in ("trace", "greedy_eval"):
        source_rows = [row for row in scenario_rows if row["metric_source"] == source]
        summary_rows.extend(_summarize_weak_coverage_cloud(source_rows, source))
        summary_rows.extend(_summarize_congested_edge_cloud(source_rows, source))
    summary_rows.extend(_summarize_semantic_cloud(trace_rows, "trace", "cloud_offload_ratio_delta"))
    summary_rows.extend(_summarize_semantic_cloud(greedy_trace_rows, "greedy_trace", "cloud_offload_ratio_delta"))
    summary_rows.extend(_summarize_semantic_cloud(policy_rows, "policy", "average_cloud_tasks_delta"))
    return summary_rows


def _summarize_weak_coverage_cloud(rows: list[CSVRow], source: str) -> list[CSVRow]:
    run_rows: list[CSVRow] = []
    for seed in sorted({int(row["seed"]) for row in rows}):
        seed_rows = [row for row in rows if int(row["seed"]) == seed]
        weak = _find_row(seed_rows, coverage_scenario="weak_coverage")
        other_cloud_values = [
            float(row["cloud_offload_ratio"]) for row in seed_rows if row["coverage_scenario"] != "weak_coverage"
        ]
        if not weak or not other_cloud_values:
            continue
        other_mean = sum(other_cloud_values) / len(other_cloud_values)
        weak_cloud = float(weak["cloud_offload_ratio"])
        run_rows.append(
            {
                "seed": seed,
                "passed": int(weak_cloud < other_mean),
                "delta": weak_cloud - other_mean,
                "primary_metric": weak_cloud,
                "threshold": other_mean,
            }
        )
    return [_summarize_runs("weak_coverage_少云", source, "", run_rows, pass_when_delta_negative=True)]


def _summarize_congested_edge_cloud(rows: list[CSVRow], source: str) -> list[CSVRow]:
    run_rows: list[CSVRow] = []
    for seed in sorted({int(row["seed"]) for row in rows}):
        seed_rows = [row for row in rows if int(row["seed"]) == seed]
        congested = _find_row(seed_rows, coverage_scenario="congested_edge")
        balanced = _find_row(seed_rows, coverage_scenario="balanced")
        if not congested or not balanced:
            continue
        congested_cloud = float(congested["cloud_offload_ratio"])
        balanced_cloud = float(balanced["cloud_offload_ratio"])
        congested_share = float(congested["cloud_share_of_remote"])
        run_rows.append(
            {
                "seed": seed,
                "passed": int(congested_cloud > balanced_cloud and congested_share >= 0.45),
                "delta": congested_cloud - balanced_cloud,
                "primary_metric": congested_cloud,
                "threshold": balanced_cloud,
                "aux_metric": congested_share,
            }
        )
    return [_summarize_runs("congested_edge_转云", source, "", run_rows, pass_when_delta_negative=False)]


def _summarize_semantic_cloud(rows: list[CSVRow], source: str, delta_key: str) -> list[CSVRow]:
    summary_rows: list[CSVRow] = []
    for field in SEMANTIC_FIELDS:
        field_rows = [row for row in rows if row["semantic_field"] == field]
        run_rows = [
            {
                "seed": int(row["seed"]),
                "passed": int(float(row[delta_key]) < 0.0),
                "delta": float(row[delta_key]),
                "primary_metric": float(row[delta_key]),
                "threshold": 0.0,
            }
            for row in field_rows
        ]
        summary_rows.append(
            _summarize_runs(
                f"{field}_抑制云端卸载",
                source,
                field,
                run_rows,
                pass_when_delta_negative=True,
            )
        )
    return summary_rows


def _summarize_runs(
    hypothesis: str,
    source: str,
    semantic_field: str,
    rows: list[CSVRow],
    *,
    pass_when_delta_negative: bool,
) -> CSVRow:
    if not rows:
        return {
            "hypothesis": hypothesis,
            "source": source,
            "semantic_field": semantic_field,
            "run_count": 0,
            "stable_count": 0,
            "stable_ratio": 0.0,
            "passed": 0,
            "mean_delta": 0.0,
            "min_delta": 0.0,
            "max_delta": 0.0,
            "mean_primary_metric": 0.0,
            "mean_threshold": 0.0,
            "mean_aux_metric": 0.0,
        }
    deltas = [float(row["delta"]) for row in rows]
    primary_values = [float(row["primary_metric"]) for row in rows]
    thresholds = [float(row["threshold"]) for row in rows]
    aux_values = [float(row.get("aux_metric", 0.0)) for row in rows]
    stable_count = sum(int(row["passed"]) for row in rows)
    stable_ratio = stable_count / len(rows)
    mean_delta = sum(deltas) / len(deltas)
    mean_aux_metric = sum(aux_values) / len(aux_values)
    direction_ok = mean_delta < 0.0 if pass_when_delta_negative else mean_delta > 0.0
    aux_ok = mean_aux_metric >= 0.45 if hypothesis == "congested_edge_转云" else True
    return {
        "hypothesis": hypothesis,
        "source": source,
        "semantic_field": semantic_field,
        "run_count": len(rows),
        "stable_count": stable_count,
        "stable_ratio": stable_ratio,
        "passed": int(stable_ratio >= 0.8 and direction_ok and aux_ok),
        "mean_delta": mean_delta,
        "min_delta": min(deltas),
        "max_delta": max(deltas),
        "mean_primary_metric": sum(primary_values) / len(primary_values),
        "mean_threshold": sum(thresholds) / len(thresholds),
        "mean_aux_metric": mean_aux_metric,
    }


def _build_semantic_hypothesis_rows(rows: list[CSVRow], source: str, delta_key: str) -> list[CSVRow]:
    hypothesis_rows: list[CSVRow] = []
    for field in SEMANTIC_FIELDS:
        field_rows = [row for row in rows if row["semantic_field"] == field]
        deltas = [float(row[delta_key]) for row in field_rows]
        stable_count = sum(1 for delta in deltas if delta < 0.0)
        stable_ratio = stable_count / len(deltas) if deltas else 0.0
        mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
        hypothesis_rows.append(
            {
                "hypothesis": f"{field}_抑制云端卸载",
                "source": source,
                "semantic_field": field,
                "passed": int(stable_ratio >= 0.8 and mean_delta < 0.0),
                "primary_metric": stable_ratio,
                "threshold": 0.8,
                "detail": f"{source} 中 {field} 的云端 delta 均值={mean_delta:.3f}，稳定比例={stable_ratio:.3f}。",
            }
        )
    return hypothesis_rows


def _build_notes(rows: list[CSVRow]) -> dict[str, str]:
    notes = {
        "summary": "passed=1 表示该假设按当前阈值成立；trace 是训练轨迹，policy 是训练后策略表。",
        "weak_coverage_rule": "weak_coverage_少云 要求 weak_coverage 的 cloud_offload_ratio 低于其他场景均值。",
        "congested_edge_rule": "congested_edge_转云 要求 congested_edge 的 cloud_offload_ratio 高于 balanced，且云端占远端卸载比例不低于 0.45。",
        "semantic_rule": "语义抑制云端卸载要求 high_level=2 相对 low_level=0 的云端指标 delta<0，且跨场景稳定比例不低于 0.8。",
    }
    for row in rows:
        notes[str(row["hypothesis"]) + "_" + str(row["source"])] = str(row["detail"])
    return notes


def _build_stability_notes(rows: list[CSVRow]) -> dict[str, str]:
    notes = {
        "summary": "stable_ratio 表示该假设在多 seed/多场景样本中成立的比例；passed=1 表示 stable_ratio>=0.8 且均值方向符合预期。",
        "source_note": "trace 是训练轨迹，greedy_eval 是训练后无探索部署评估，policy 是训练后策略表。",
        "weak_coverage_rule": "weak_coverage_少云 要求 weak_coverage 的云端卸载比例低于同 seed 其他场景均值。",
        "congested_edge_rule": "congested_edge_转云 要求 congested_edge 云端卸载比例高于 balanced，且云端占远端卸载均值不低于 0.45。",
        "semantic_rule": "语义抑制云端卸载要求 high_level=2 相对 low_level=0 的云端指标 delta<0。",
    }
    for row in rows:
        key = f"{row['hypothesis']}_{row['source']}"
        notes[key] = (
            f"stable_ratio={float(row['stable_ratio']):.3f}, "
            f"mean_delta={float(row['mean_delta']):.3f}, "
            f"passed={int(row['passed'])}。"
        )
    return notes


def _trace_remote_metrics(rows: list[dict[str, str]]) -> dict[str, float]:
    processed = sum(
        _to_int(row["executed_local_tasks"])
        + _to_int(row["executed_offload_tasks"])
        + _to_int(row.get("executed_cloud_tasks", "0"))
        for row in rows
    )
    edge = sum(_to_int(row["executed_offload_tasks"]) for row in rows)
    cloud = sum(_to_int(row.get("executed_cloud_tasks", "0")) for row in rows)
    return {
        "offload_ratio": (edge + cloud) / processed if processed else 0.0,
        "edge_offload_ratio": edge / processed if processed else 0.0,
        "cloud_offload_ratio": cloud / processed if processed else 0.0,
    }


def _cloud_preferred_ratio(rows: list[dict[str, str]]) -> float:
    if not rows:
        return 0.0
    preferred = sum(
        1
        for row in rows
        if _to_int(row.get("cloud_tasks", "0")) > max(_to_int(row["local_tasks"]), _to_int(row["offload_tasks"]))
    )
    return preferred / len(rows)


def _find_row(rows: list[CSVRow], **conditions: str) -> CSVRow | None:
    for row in rows:
        if all(str(row.get(key)) == value for key, value in conditions.items()):
            return row
    return None


def _stringify_rows(rows: list[dict[str, CSVValue]]) -> list[dict[str, str]]:
    return [{key: str(value) for key, value in row.items()} for row in rows]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_table(csv_path: Path, json_path: Path, rows: list[CSVRow]) -> None:
    if not rows:
        raise ValueError(f"rows must not be empty for {csv_path}")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _mean(rows: list[dict[str, str]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(_to_float(row[field]) for row in rows) / len(rows)


def _to_float(value: str) -> float:
    return float(value)


def _to_int(value: str) -> int:
    return int(float(value))
