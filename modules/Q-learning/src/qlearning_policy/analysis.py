# 中文说明：本文件读取多场景策略实验产物，生成策略表现和动作倾向解释表。
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .offloading import OffloadingAction, OffloadingEnv, OffloadingState
from .scenarios import make_offloading_config_for_coverage


CSVValue = float | int | str
CSVRow = dict[str, CSVValue]
GROUP_FIELDS: tuple[tuple[str, str | None], ...] = (
    ("overall", None),
    ("link", "link"),
    ("edge_load", "edge_load"),
    ("cloud_load", "cloud_load"),
    ("battery", "battery"),
    ("task_urgency", "task_urgency"),
    ("data_sensitivity", "data_sensitivity"),
    ("area_risk", "area_risk"),
)


def analyze_scenario_sweep(input_dir: Path, output_dir: Path | None = None) -> dict[str, str]:
    """分析 run-scenarios 产物，不重新训练策略。"""

    output_dir = output_dir or input_dir / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows = _read_csv(input_dir / "scenario_strategy_metrics.csv")
    scenario_names = sorted({str(row["coverage_scenario"]) for row in metrics_rows})

    best_rows = build_best_strategy_rows(metrics_rows)
    qlearning_rows = build_qlearning_summary_rows(metrics_rows, best_rows)
    trace_rows = build_trace_action_summary_rows(input_dir, scenario_names)
    trace_action_class_rows = build_trace_action_class_summary_rows(input_dir, scenario_names)
    policy_rows = build_policy_action_summary_rows(input_dir, scenario_names)
    reward_diagnostic_rows = build_reward_diagnostic_rows(scenario_names)
    notes = build_analysis_notes(best_rows, qlearning_rows, trace_rows, trace_action_class_rows, reward_diagnostic_rows)

    artifacts = {
        "scenario_best_strategy_csv": str(output_dir / "scenario_best_strategy.csv"),
        "scenario_best_strategy_json": str(output_dir / "scenario_best_strategy.json"),
        "qlearning_scenario_summary_csv": str(output_dir / "qlearning_scenario_summary.csv"),
        "qlearning_scenario_summary_json": str(output_dir / "qlearning_scenario_summary.json"),
        "qlearning_trace_action_summary_csv": str(output_dir / "qlearning_trace_action_summary.csv"),
        "qlearning_trace_action_summary_json": str(output_dir / "qlearning_trace_action_summary.json"),
        "qlearning_trace_action_class_summary_csv": str(output_dir / "qlearning_trace_action_class_summary.csv"),
        "qlearning_trace_action_class_summary_json": str(output_dir / "qlearning_trace_action_class_summary.json"),
        "qlearning_policy_action_summary_csv": str(output_dir / "qlearning_policy_action_summary.csv"),
        "qlearning_policy_action_summary_json": str(output_dir / "qlearning_policy_action_summary.json"),
        "reward_diagnostics_csv": str(output_dir / "reward_diagnostics.csv"),
        "reward_diagnostics_json": str(output_dir / "reward_diagnostics.json"),
        "analysis_notes_json": str(output_dir / "analysis_notes.json"),
    }

    _write_table(Path(artifacts["scenario_best_strategy_csv"]), Path(artifacts["scenario_best_strategy_json"]), best_rows)
    _write_table(
        Path(artifacts["qlearning_scenario_summary_csv"]),
        Path(artifacts["qlearning_scenario_summary_json"]),
        qlearning_rows,
    )
    _write_table(
        Path(artifacts["qlearning_trace_action_summary_csv"]),
        Path(artifacts["qlearning_trace_action_summary_json"]),
        trace_rows,
    )
    _write_table(
        Path(artifacts["qlearning_trace_action_class_summary_csv"]),
        Path(artifacts["qlearning_trace_action_class_summary_json"]),
        trace_action_class_rows,
    )
    _write_table(
        Path(artifacts["qlearning_policy_action_summary_csv"]),
        Path(artifacts["qlearning_policy_action_summary_json"]),
        policy_rows,
    )
    _write_table(
        Path(artifacts["reward_diagnostics_csv"]),
        Path(artifacts["reward_diagnostics_json"]),
        reward_diagnostic_rows,
    )
    Path(artifacts["analysis_notes_json"]).write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")

    return artifacts


def analyze_single_run(input_dir: Path, output_dir: Path | None = None, scenario_name: str = "run") -> dict[str, str]:
    """分析单个 run-demo 输出目录，适合长训练或专项实验。"""

    output_dir = output_dir or input_dir / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    trace_rows_raw = _read_csv(input_dir / "decision_trace.csv")
    policy_rows_raw = _read_csv(input_dir / "policy_table.csv")
    trace_rows = build_trace_action_summary_from_rows(scenario_name, trace_rows_raw)
    trace_action_class_rows = build_trace_action_class_summary_from_rows(scenario_name, trace_rows_raw)
    policy_rows = build_policy_action_summary_from_rows(scenario_name, policy_rows_raw)
    notes = build_single_run_notes(trace_rows, policy_rows)

    artifacts = {
        "qlearning_trace_action_summary_csv": str(output_dir / "qlearning_trace_action_summary.csv"),
        "qlearning_trace_action_summary_json": str(output_dir / "qlearning_trace_action_summary.json"),
        "qlearning_trace_action_class_summary_csv": str(output_dir / "qlearning_trace_action_class_summary.csv"),
        "qlearning_trace_action_class_summary_json": str(output_dir / "qlearning_trace_action_class_summary.json"),
        "qlearning_policy_action_summary_csv": str(output_dir / "qlearning_policy_action_summary.csv"),
        "qlearning_policy_action_summary_json": str(output_dir / "qlearning_policy_action_summary.json"),
        "analysis_notes_json": str(output_dir / "analysis_notes.json"),
    }
    _write_table(
        Path(artifacts["qlearning_trace_action_summary_csv"]),
        Path(artifacts["qlearning_trace_action_summary_json"]),
        trace_rows,
    )
    _write_table(
        Path(artifacts["qlearning_trace_action_class_summary_csv"]),
        Path(artifacts["qlearning_trace_action_class_summary_json"]),
        trace_action_class_rows,
    )
    _write_table(
        Path(artifacts["qlearning_policy_action_summary_csv"]),
        Path(artifacts["qlearning_policy_action_summary_json"]),
        policy_rows,
    )
    Path(artifacts["analysis_notes_json"]).write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifacts


def build_best_strategy_rows(metrics_rows: list[dict[str, str]]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    for scenario_name in sorted({row["coverage_scenario"] for row in metrics_rows}):
        scenario_rows = [row for row in metrics_rows if row["coverage_scenario"] == scenario_name]
        best = max(scenario_rows, key=lambda row: _to_float(row["average_reward"]))
        qlearning = _find_strategy_row(scenario_rows, "q_learning")
        rows.append(
            {
                "coverage_scenario": scenario_name,
                "best_strategy": best["strategy"],
                "best_average_reward": _to_float(best["average_reward"]),
                "best_offload_ratio": _to_float(best["offload_ratio"]),
                "q_learning_average_reward": _to_float(qlearning["average_reward"]),
                "q_learning_reward_gap_to_best": _to_float(best["average_reward"])
                - _to_float(qlearning["average_reward"]),
                "q_learning_offload_ratio": _to_float(qlearning["offload_ratio"]),
            }
        )
    return rows


def build_qlearning_summary_rows(metrics_rows: list[dict[str, str]], best_rows: list[CSVRow]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    best_by_scenario = {row["coverage_scenario"]: row for row in best_rows}
    for scenario_name in sorted({row["coverage_scenario"] for row in metrics_rows}):
        qlearning = _find_strategy_row(
            [row for row in metrics_rows if row["coverage_scenario"] == scenario_name],
            "q_learning",
        )
        best = best_by_scenario[scenario_name]
        rows.append(
            {
                "coverage_scenario": scenario_name,
                "average_reward": _to_float(qlearning["average_reward"]),
                "average_delay": _to_float(qlearning["average_delay"]),
                "average_energy": _to_float(qlearning["average_energy"]),
                "average_queue": _to_float(qlearning["average_queue"]),
                "processed_tasks": _to_int(qlearning["processed_tasks"]),
                "offload_ratio": _to_float(qlearning["offload_ratio"]),
                "edge_offload_ratio": _to_float(qlearning.get("edge_offload_ratio", qlearning["offload_ratio"])),
                "cloud_offload_ratio": _to_float(qlearning.get("cloud_offload_ratio", "0")),
                "best_strategy": str(best["best_strategy"]),
                "reward_gap_to_best": float(best["q_learning_reward_gap_to_best"]),
            }
        )
    return rows


def build_trace_action_summary_rows(input_dir: Path, scenario_names: list[str]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    for scenario_name in scenario_names:
        trace_rows = _read_csv(input_dir / scenario_name / "decision_trace.csv")
        rows.extend(build_trace_action_summary_from_rows(scenario_name, trace_rows))
    return rows


def build_trace_action_summary_from_rows(scenario_name: str, trace_rows: list[dict[str, str]]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    for group_by, field in GROUP_FIELDS:
        if field is None or field in trace_rows[0]:
            rows.extend(_summarize_trace_group(scenario_name, trace_rows, group_by, field))
    return rows


def build_trace_action_class_summary_rows(input_dir: Path, scenario_names: list[str]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    for scenario_name in scenario_names:
        trace_rows = _read_csv(input_dir / scenario_name / "decision_trace.csv")
        rows.extend(build_trace_action_class_summary_from_rows(scenario_name, trace_rows))
    return rows


def build_trace_action_class_summary_from_rows(scenario_name: str, trace_rows: list[dict[str, str]]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    for group_by, field in GROUP_FIELDS:
        if field is not None and field not in trace_rows[0]:
            continue
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        if field is None:
            grouped["all"] = trace_rows
        else:
            for row in trace_rows:
                grouped[row[field]].append(row)
        for group_value, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
            action_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in group_rows:
                action_groups[_trace_action_class(row)].append(row)
            for action_class, action_rows in sorted(action_groups.items(), key=lambda item: item[0]):
                processed = sum(
                    _to_int(row["executed_local_tasks"])
                    + _to_int(row["executed_offload_tasks"])
                    + _to_int(row.get("executed_cloud_tasks", "0"))
                    for row in action_rows
                )
                edge_offloaded = sum(_to_int(row["executed_offload_tasks"]) for row in action_rows)
                cloud_offloaded = sum(_to_int(row.get("executed_cloud_tasks", "0")) for row in action_rows)
                offloaded = edge_offloaded + cloud_offloaded
                rows.append(
                    {
                        "coverage_scenario": scenario_name,
                        "group_by": group_by,
                        "group_value": group_value,
                        "action_class": action_class,
                        "slots": len(action_rows),
                        "slot_ratio_in_group": len(action_rows) / len(group_rows) if group_rows else 0.0,
                        "average_queue": _mean(action_rows, "queue"),
                        "average_reward": _mean(action_rows, "reward"),
                        "processed_tasks": processed,
                        "offloaded_tasks": offloaded,
                        "edge_offloaded_tasks": edge_offloaded,
                        "cloud_offloaded_tasks": cloud_offloaded,
                        "offload_ratio": offloaded / processed if processed else 0.0,
                        "edge_offload_ratio": edge_offloaded / processed if processed else 0.0,
                        "cloud_offload_ratio": cloud_offloaded / processed if processed else 0.0,
                    }
                )
    return rows


def build_policy_action_summary_rows(input_dir: Path, scenario_names: list[str]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    for scenario_name in scenario_names:
        policy_rows = _read_csv(input_dir / scenario_name / "policy_table.csv")
        rows.extend(build_policy_action_summary_from_rows(scenario_name, policy_rows))
    return rows


def build_policy_action_summary_from_rows(scenario_name: str, policy_rows: list[dict[str, str]]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    for group_by, field in GROUP_FIELDS:
        if field is None or field in policy_rows[0]:
            rows.extend(_summarize_policy_group(scenario_name, policy_rows, group_by, field))
    return rows


def build_reward_diagnostic_rows(scenario_names: list[str]) -> list[CSVRow]:
    rows: list[CSVRow] = []
    queue_values = (1, 2, 4, 8, 16)
    battery = 4
    for scenario_name in scenario_names:
        config = make_offloading_config_for_coverage(scenario_name)
        env = OffloadingEnv(config=config, seed=0)
        for queue in queue_values:
            for link in range(len(config.link_rates_bps)):
                for edge_load in range(len(config.edge_load_levels)):
                    for cloud_load in range(len(config.cloud_load_levels)):
                        state = OffloadingState(
                            queue=queue,
                            link=link,
                            battery=battery,
                            edge_load=edge_load,
                            cloud_load=cloud_load,
                            task_urgency=1,
                            data_sensitivity=1,
                            area_risk=1,
                        )
                        state_rows: list[CSVRow] = []
                        for action in env.actions:
                            breakdown = env.compute_reward(state, action)
                            state_rows.append(
                                {
                                    "coverage_scenario": scenario_name,
                                    "queue": queue,
                                    "link": link,
                                    "link_rate_bps": float(config.link_rates_bps[link]),
                                    "battery": battery,
                                    "edge_load": edge_load,
                                    "edge_load_value": float(config.edge_load_levels[edge_load]),
                                    "cloud_load": cloud_load,
                                    "cloud_load_value": float(config.cloud_load_levels[cloud_load]),
                                    "task_urgency": state.task_urgency,
                                    "data_sensitivity": state.data_sensitivity,
                                    "area_risk": state.area_risk,
                                    "requested_local_tasks": action.local_tasks,
                                    "requested_offload_tasks": action.offload_tasks,
                                    "requested_cloud_tasks": action.cloud_tasks,
                                    "executed_local_tasks": breakdown.executed_action.local_tasks,
                                    "executed_offload_tasks": breakdown.executed_action.offload_tasks,
                                    "executed_cloud_tasks": breakdown.executed_action.cloud_tasks,
                                    "action_class": _executed_action_class(breakdown.executed_action),
                                    "is_illegal": int(breakdown.illegal_penalty > 0.0),
                                    "reward": breakdown.reward,
                                    "utility": breakdown.utility,
                                    "delay": breakdown.delay,
                                    "energy": breakdown.energy,
                                    "queue_penalty": breakdown.queue_penalty,
                                    "illegal_penalty": breakdown.illegal_penalty,
                                    "low_link_offload_penalty": breakdown.low_link_offload_penalty,
                                    "urgency_delay_penalty": breakdown.urgency_delay_penalty,
                                    "deadline_miss_penalty": breakdown.deadline_miss_penalty,
                                    "data_sensitivity_penalty": breakdown.data_sensitivity_penalty,
                                    "area_risk_penalty": breakdown.area_risk_penalty,
                                    "cloud_usage_penalty": breakdown.cloud_usage_penalty,
                                    "low_link_cloud_penalty": breakdown.low_link_cloud_penalty,
                                    "edge_congestion_penalty": breakdown.edge_congestion_penalty,
                                    "cloud_congestion_relief_bonus": breakdown.cloud_congestion_relief_bonus,
                                }
                            )
                        ranked = sorted(state_rows, key=lambda row: float(row["reward"]), reverse=True)
                        for rank, row in enumerate(ranked, start=1):
                            row["rank_by_reward"] = rank
                        rows.extend(ranked)
    return rows


def build_analysis_notes(
    best_rows: list[CSVRow],
    qlearning_rows: list[CSVRow],
    trace_rows: list[CSVRow],
    trace_action_class_rows: list[CSVRow],
    reward_diagnostic_rows: list[CSVRow],
) -> dict[str, str]:
    q_best_count = sum(1 for row in best_rows if row["best_strategy"] == "q_learning")
    notes = {
        "summary": f"Q-learning 在 {q_best_count}/{len(best_rows)} 个覆盖场景中取得最高平均 reward。",
        "how_to_read": "先看 scenario_best_strategy，再看 qlearning_trace_action_summary 中 group_by=link/edge_load 的行判断动作倾向。",
        "metric_scope_warning": "当前 scenario_strategy_metrics 中的 q_learning 行来自训练轨迹，包含 epsilon 探索动作；它适合看训练过程表现，但还不等同于训练后无探索部署策略。",
    }

    weak = _find_csv_row(qlearning_rows, coverage_scenario="weak_coverage")
    weak_overall = _find_csv_row(trace_rows, coverage_scenario="weak_coverage", group_by="overall", group_value="all")
    weak_low_link_hybrid = (
        _find_csv_row(
            trace_action_class_rows,
            coverage_scenario="weak_coverage",
            group_by="link",
            group_value="0",
            action_class="local_edge_hybrid",
        )
        or _find_csv_row(
            trace_action_class_rows,
            coverage_scenario="weak_coverage",
            group_by="link",
            group_value="0",
            action_class="edge_cloud_hybrid",
        )
        or _find_csv_row(
            trace_action_class_rows,
            coverage_scenario="weak_coverage",
            group_by="link",
            group_value="0",
            action_class="local_cloud_hybrid",
        )
        or _find_csv_row(
            trace_action_class_rows,
            coverage_scenario="weak_coverage",
            group_by="link",
            group_value="0",
            action_class="three_tier",
        )
    )
    weak_low_link_reward_top = _find_csv_row(
        reward_diagnostic_rows,
        coverage_scenario="weak_coverage",
        queue="16",
        link="0",
        edge_load="1",
        rank_by_reward="1",
    )
    if weak and weak_overall:
        notes["weak_coverage_note"] = (
            "弱覆盖下 Q-learning 仍会保留部分卸载，是因为当前 reward 不是硬规则禁止卸载，"
            "而是在时延、能耗、队列积压和长期收益之间折中。"
            f"本次弱覆盖场景 Q-learning 总体卸载比例为 {float(weak['offload_ratio']):.3f}，"
            f"实际轨迹中的混合动作时隙比例为 {float(weak_overall['hybrid_slot_ratio']):.3f}。"
        )
    if weak_low_link_hybrid:
        notes["weak_low_link_trace_note"] = (
            "弱覆盖且低链路档位 link=0 时，混合动作在训练轨迹中占比 "
            f"{float(weak_low_link_hybrid['slot_ratio_in_group']):.3f}，"
            f"平均 reward 为 {float(weak_low_link_hybrid['average_reward']):.3f}。"
        )
    if weak_low_link_reward_top:
        notes["weak_low_link_reward_note"] = (
            "在代表性状态 queue=16、link=0、battery=4、edge_load=1 下，"
            "即时 reward 排名第一的动作是 "
            f"local={weak_low_link_reward_top['executed_local_tasks']}, "
            f"offload={weak_low_link_reward_top['executed_offload_tasks']}，"
            f"reward={float(weak_low_link_reward_top['reward']):.3f}。"
            "这说明高队列场景中，混合动作因处理任务更多而获得更高 utility，"
            "当前链路惩罚不足以压过这部分收益。"
        )
    return notes


def build_single_run_notes(trace_rows: list[CSVRow], policy_rows: list[CSVRow]) -> dict[str, str]:
    notes = {
        "summary": "单次实验分析已按链路、边缘负载、电量和任务语义分组。",
        "metric_scope_warning": "trace 统计来自训练轨迹，包含 epsilon 探索；policy 统计来自训练后策略表，但未访问状态的 Q 值可能仍接近初始值。",
    }
    for group_by in ("task_urgency", "data_sensitivity", "area_risk"):
        group_rows = [row for row in trace_rows if row["group_by"] == group_by]
        if group_rows:
            low = _find_csv_row(group_rows, group_value="0")
            high = _find_csv_row(group_rows, group_value="2")
            if low and high:
                notes[f"{group_by}_trace_note"] = (
                    f"训练轨迹中 {group_by}=0 的卸载比例为 {float(low['offload_ratio']):.3f}，"
                    f"{group_by}=2 的卸载比例为 {float(high['offload_ratio']):.3f}。"
                )
        policy_group_rows = [row for row in policy_rows if row["group_by"] == group_by]
        if policy_group_rows:
            low_policy = _find_csv_row(policy_group_rows, group_value="0")
            high_policy = _find_csv_row(policy_group_rows, group_value="2")
            if low_policy and high_policy:
                notes[f"{group_by}_policy_note"] = (
                    f"策略表中 {group_by}=0 的平均卸载任务数为 {float(low_policy['average_offload_tasks']):.3f}，"
                    f"{group_by}=2 的平均卸载任务数为 {float(high_policy['average_offload_tasks']):.3f}。"
                )
    return notes


def _summarize_trace_group(
    scenario_name: str,
    rows: list[dict[str, str]],
    group_by: str,
    field: str | None,
) -> list[CSVRow]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    if field is None:
        grouped["all"] = rows
    else:
        for row in rows:
            grouped[row[field]].append(row)

    summary_rows: list[CSVRow] = []
    for group_value, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
        slots = len(group_rows)
        processed = sum(
            _to_int(row["executed_local_tasks"])
            + _to_int(row["executed_offload_tasks"])
            + _to_int(row.get("executed_cloud_tasks", "0"))
            for row in group_rows
        )
        edge_offloaded = sum(_to_int(row["executed_offload_tasks"]) for row in group_rows)
        cloud_offloaded = sum(_to_int(row.get("executed_cloud_tasks", "0")) for row in group_rows)
        offloaded = edge_offloaded + cloud_offloaded
        local_only_slots = sum(
            1
            for row in group_rows
            if _to_int(row["executed_local_tasks"]) > 0
            and _to_int(row["executed_offload_tasks"]) == 0
            and _to_int(row.get("executed_cloud_tasks", "0")) == 0
        )
        offload_only_slots = sum(
            1
            for row in group_rows
            if _to_int(row["executed_local_tasks"]) == 0
            and _to_int(row["executed_offload_tasks"]) > 0
            and _to_int(row.get("executed_cloud_tasks", "0")) == 0
        )
        cloud_only_slots = sum(
            1
            for row in group_rows
            if _to_int(row["executed_local_tasks"]) == 0
            and _to_int(row["executed_offload_tasks"]) == 0
            and _to_int(row.get("executed_cloud_tasks", "0")) > 0
        )
        hybrid_slots = sum(
            1
            for row in group_rows
            if _positive_part_count(
                _to_int(row["executed_local_tasks"]),
                _to_int(row["executed_offload_tasks"]),
                _to_int(row.get("executed_cloud_tasks", "0")),
            )
            >= 2
        )
        idle_slots = slots - local_only_slots - offload_only_slots - hybrid_slots
        idle_slots -= cloud_only_slots
        summary_rows.append(
            {
                "coverage_scenario": scenario_name,
                "group_by": group_by,
                "group_value": group_value,
                "slots": slots,
                "average_queue": _mean(group_rows, "queue"),
                "average_reward": _mean(group_rows, "reward"),
                "processed_tasks": processed,
                "offloaded_tasks": offloaded,
                "edge_offloaded_tasks": edge_offloaded,
                "cloud_offloaded_tasks": cloud_offloaded,
                "offload_ratio": offloaded / processed if processed else 0.0,
                "edge_offload_ratio": edge_offloaded / processed if processed else 0.0,
                "cloud_offload_ratio": cloud_offloaded / processed if processed else 0.0,
                "local_only_slot_ratio": local_only_slots / slots if slots else 0.0,
                "offload_only_slot_ratio": offload_only_slots / slots if slots else 0.0,
                "cloud_only_slot_ratio": cloud_only_slots / slots if slots else 0.0,
                "hybrid_slot_ratio": hybrid_slots / slots if slots else 0.0,
                "idle_slot_ratio": idle_slots / slots if slots else 0.0,
            }
        )
    return summary_rows


def _summarize_policy_group(
    scenario_name: str,
    rows: list[dict[str, str]],
    group_by: str,
    field: str | None,
) -> list[CSVRow]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    if field is None:
        grouped["all"] = rows
    else:
        for row in rows:
            grouped[row[field]].append(row)

    summary_rows: list[CSVRow] = []
    for group_value, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
        states = len(group_rows)
        local_tasks = [_to_int(row["local_tasks"]) for row in group_rows]
        offload_tasks = [_to_int(row["offload_tasks"]) for row in group_rows]
        cloud_tasks = [_to_int(row.get("cloud_tasks", "0")) for row in group_rows]
        remote_tasks = [edge + cloud for edge, cloud in zip(offload_tasks, cloud_tasks, strict=True)]
        offload_preferred = sum(1 for local, remote in zip(local_tasks, remote_tasks, strict=True) if remote > local)
        local_preferred = sum(1 for local, remote in zip(local_tasks, remote_tasks, strict=True) if local > remote)
        cloud_preferred = sum(1 for cloud, local, edge in zip(cloud_tasks, local_tasks, offload_tasks, strict=True) if cloud > max(local, edge))
        hybrid = sum(
            1
            for local, edge, cloud in zip(local_tasks, offload_tasks, cloud_tasks, strict=True)
            if _positive_part_count(local, edge, cloud) >= 2
        )
        idle = sum(
            1
            for local, edge, cloud in zip(local_tasks, offload_tasks, cloud_tasks, strict=True)
            if local == 0 and edge == 0 and cloud == 0
        )
        summary_rows.append(
            {
                "coverage_scenario": scenario_name,
                "group_by": group_by,
                "group_value": group_value,
                "states": states,
                "average_local_tasks": sum(local_tasks) / states if states else 0.0,
                "average_offload_tasks": sum(offload_tasks) / states if states else 0.0,
                "average_cloud_tasks": sum(cloud_tasks) / states if states else 0.0,
                "average_remote_tasks": sum(remote_tasks) / states if states else 0.0,
                "offload_preferred_state_ratio": offload_preferred / states if states else 0.0,
                "local_preferred_state_ratio": local_preferred / states if states else 0.0,
                "cloud_preferred_state_ratio": cloud_preferred / states if states else 0.0,
                "hybrid_state_ratio": hybrid / states if states else 0.0,
                "idle_state_ratio": idle / states if states else 0.0,
            }
        )
    return summary_rows


def _find_strategy_row(rows: list[dict[str, str]], strategy: str) -> dict[str, str]:
    for row in rows:
        if row["strategy"] == strategy:
            return row
    raise ValueError(f"missing strategy row: {strategy}")


def _find_csv_row(rows: list[CSVRow], **conditions: str) -> CSVRow | None:
    for row in rows:
        if all(str(row.get(key)) == value for key, value in conditions.items()):
            return row
    return None


def _trace_action_class(row: dict[str, str]) -> str:
    return _action_class(
        _to_int(row["executed_local_tasks"]),
        _to_int(row["executed_offload_tasks"]),
        _to_int(row.get("executed_cloud_tasks", "0")),
    )


def _executed_action_class(action: OffloadingAction) -> str:
    return _action_class(action.local_tasks, action.offload_tasks, action.cloud_tasks)


def _action_class(local_tasks: int, offload_tasks: int, cloud_tasks: int) -> str:
    active_parts = _positive_part_count(local_tasks, offload_tasks, cloud_tasks)
    if active_parts >= 3:
        return "three_tier"
    if active_parts == 2:
        if local_tasks > 0 and offload_tasks > 0:
            return "local_edge_hybrid"
        if local_tasks > 0 and cloud_tasks > 0:
            return "local_cloud_hybrid"
        return "edge_cloud_hybrid"
    if local_tasks > 0:
        return "local_only"
    if offload_tasks > 0:
        return "edge_only"
    if cloud_tasks > 0:
        return "cloud_only"
    return "idle"


def _positive_part_count(local_tasks: int, offload_tasks: int, cloud_tasks: int) -> int:
    return int(local_tasks > 0) + int(offload_tasks > 0) + int(cloud_tasks > 0)


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
