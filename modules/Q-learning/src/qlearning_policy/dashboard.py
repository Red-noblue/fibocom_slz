# 中文说明：本文件把策略实验产物整理为前端仪表盘可直接消费的 JSON 数据。
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .offloading import OffloadingConfig
from .interface import PolicyStatePayload, build_interface_contract, decide_policy
from .scenarios import COVERAGE_SCENARIOS, make_offloading_config_for_coverage
from .simulation import build_policy_table_rows, train_q_learning


DASHBOARD_SCHEMA_VERSION = "qlearning_policy.dashboard.v1"
DEFAULT_STABILITY_DIR = Path("outputs/qlearning_policy/three_tier_stability_reward_v5")
DEFAULT_SCENARIO_DIR = Path("outputs/qlearning_policy/scenario_sweep")
DEFAULT_DASHBOARD_OUTPUT = Path("web/static/data/policy-dashboard.json")
DEFAULT_TRAINED_POLICY_OUTPUT = Path("web/static/data/trained-q-policy.json")
POLICY_STATE_FIELD_ORDER = (
    "queue",
    "link",
    "battery",
    "edge_load",
    "cloud_load",
    "task_urgency",
    "data_sensitivity",
    "area_risk",
)


def build_dashboard_payload(
    *,
    stability_dir: Path = DEFAULT_STABILITY_DIR,
    scenario_dir: Path = DEFAULT_SCENARIO_DIR,
) -> dict[str, Any]:
    """读取当前模块产物，生成独立前端展示数据。"""

    stability_rows = _read_csv(stability_dir / "three_tier_stability_summary.csv")
    seed_metric_rows = _read_csv(stability_dir / "three_tier_seed_scenario_metrics.csv")
    scenario_metric_rows = _read_csv(scenario_dir / "scenario_strategy_metrics.csv")
    sample_state = PolicyStatePayload(
        queue=10,
        link=2,
        battery=4,
        edge_load=2,
        cloud_load=0,
        task_urgency=1,
        data_sensitivity=0,
        area_risk=0,
    )
    sample_decision = decide_policy(sample_state, scenario_name="congested_edge")

    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": {
            "name": "Q-learning 低空策略决策模块",
            "role": "端-边-云计算卸载策略决策层",
            "frontend_scope": "本前端仅展示本模块策略实验与接口试算，不接管 uav_virtual_validation 前端。",
        },
        "interface_contract": build_interface_contract(),
        "coverage_scenarios": _build_coverage_scenario_rows(),
        "simulator_config": _build_simulator_config(),
        "sample_decision": sample_decision.as_dict(),
        "stability": {
            "source_dir": str(stability_dir),
            "rows": stability_rows,
            "summary": _build_stability_overview(stability_rows),
        },
        "scenario_metrics": {
            "source_dir": str(scenario_dir),
            "rows": scenario_metric_rows,
            "qlearning_rows": [
                row for row in scenario_metric_rows if row.get("strategy") == "q_learning"
            ],
        },
        "seed_metrics": {
            "source_dir": str(stability_dir),
            "rows": seed_metric_rows,
        },
        "key_findings": _build_key_findings(stability_rows),
    }


def export_dashboard_payload(
    *,
    stability_dir: Path = DEFAULT_STABILITY_DIR,
    scenario_dir: Path = DEFAULT_SCENARIO_DIR,
    output_path: Path = DEFAULT_DASHBOARD_OUTPUT,
) -> dict[str, str]:
    """生成前端 JSON 文件，并返回产物路径。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_dashboard_payload(stability_dir=stability_dir, scenario_dir=scenario_dir)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "dashboard_json": str(output_path),
        "stability_dir": str(stability_dir),
        "scenario_dir": str(scenario_dir),
    }


def export_trained_policy_snapshot(
    *,
    scenario_names: tuple[str, ...],
    slots: int,
    seed: int,
    output_path: Path = DEFAULT_TRAINED_POLICY_OUTPUT,
) -> dict[str, str | int | list[str]]:
    """训练当前 Q-learning 策略并导出给前端查表使用的紧凑 JSON。"""

    if slots <= 0:
        raise ValueError("slots must be positive")
    if not scenario_names:
        raise ValueError("scenario_names must not be empty")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    scenarios: dict[str, Any] = {}
    for scenario_name in scenario_names:
        config = make_offloading_config_for_coverage(scenario_name)
        result = train_q_learning(config=config, slots=slots, seed=seed)
        visit_counts = _build_visit_counts(result.decision_trace)
        scenarios[scenario_name] = {
            "metrics": result.metrics.as_dict(),
            "entry_count": result.agent.q_table.shape[0],
            "visited_state_count": len(visit_counts),
            "visited_ratio": len(visit_counts) / result.agent.q_table.shape[0],
            "sample_states": _build_sample_states(visit_counts),
            "entries": _build_compact_policy_entries(build_policy_table_rows(result), visit_counts),
        }

    payload = {
        "schema_version": "qlearning_policy.trained_policy.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training": {
            "algorithm": "tabular_q_learning",
            "slots": slots,
            "seed": seed,
            "source": "qlearning_policy.simulation.train_q_learning",
        },
        "state_field_order": list(POLICY_STATE_FIELD_ORDER),
        "action_field_order": ["local_tasks", "edge_tasks", "cloud_tasks"],
        "scenarios": scenarios,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {
        "trained_policy_json": str(output_path),
        "scenario_names": list(scenario_names),
        "slots": slots,
        "seed": seed,
    }


def _build_stability_overview(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    passed = sum(1 for row in rows if _to_bool(row.get("passed")))
    critical = {
        "weak_coverage_少云": False,
        "congested_edge_转云": False,
        "area_risk_抑制云端卸载": False,
    }
    for row in rows:
        hypothesis = str(row.get("hypothesis", ""))
        if hypothesis in critical and _to_bool(row.get("passed")):
            critical[hypothesis] = True
    return {
        "total_checks": total,
        "passed_checks": passed,
        "pass_ratio": passed / total if total else 0.0,
        "scheme3_ready": total > 0 and all(critical.values()),
        "critical_checks": critical,
    }


def _build_coverage_scenario_rows() -> list[dict[str, Any]]:
    return [
        {
            "name": scenario.name,
            "description": scenario.description,
            "link_probs": list(scenario.link_probs),
            "edge_load_probs": list(scenario.edge_load_probs),
            "cloud_load_probs": list(scenario.cloud_load_probs),
        }
        for scenario in COVERAGE_SCENARIOS.values()
    ]


def _build_visit_counts(rows: tuple[Any, ...]) -> Counter[tuple[int, ...]]:
    counter: Counter[tuple[int, ...]] = Counter()
    for row in rows:
        counter[
            (
                row.queue,
                row.link,
                row.battery,
                row.edge_load,
                row.cloud_load,
                row.task_urgency,
                row.data_sensitivity,
                row.area_risk,
            )
        ] += 1
    return counter


def _build_sample_states(visit_counts: Counter[tuple[int, ...]]) -> list[list[int]]:
    return [list(state) + [count] for state, count in visit_counts.most_common(24)]


def _build_compact_policy_entries(
    rows: list[dict[str, Any]],
    visit_counts: Counter[tuple[int, ...]],
) -> list[list[float | int]]:
    entries: list[list[float | int]] = []
    for row in rows:
        state = tuple(int(row[field_name]) for field_name in POLICY_STATE_FIELD_ORDER)
        entries.append(
            [
                *state,
                int(row["local_tasks"]),
                int(row["offload_tasks"]),
                int(row["cloud_tasks"]),
                round(float(row["q_value"]), 6),
                int(visit_counts[state]),
            ]
        )
    return entries


def _build_simulator_config() -> dict[str, Any]:
    config = OffloadingConfig()
    return {
        "queue_capacity": config.queue_capacity,
        "max_local_tasks": config.max_local_tasks,
        "max_edge_tasks": config.max_offload_tasks,
        "max_cloud_tasks": config.max_cloud_tasks,
        "link_rates_bps": list(config.link_rates_bps),
        "edge_load_levels": list(config.edge_load_levels),
        "cloud_load_levels": list(config.cloud_load_levels),
        "battery_level_count": config.battery_level_count,
        "arrival_values": list(config.arrival_values),
        "avg_arrival_rate": config.avg_arrival_rate,
        "task_size_bits": config.task_size_bits,
        "cycles_per_task": config.cycles_per_task,
        "local_cpu_hz": config.local_cpu_hz,
        "beta": config.beta,
        "tx_power_watts": config.tx_power_watts,
        "theta": config.theta,
        "delay_weight": config.delay_weight,
        "energy_weight": config.energy_weight,
        "queue_weight": config.queue_weight,
        "illegal_action_penalty": config.illegal_action_penalty,
        "low_link_offload_penalty": config.low_link_offload_penalty,
        "low_link_penalty_threshold": config.low_link_penalty_threshold,
        "urgency_delay_weight": config.urgency_delay_weight,
        "task_deadlines": list(config.task_deadlines),
        "deadline_miss_penalty": config.deadline_miss_penalty,
        "data_sensitivity_offload_penalty": config.data_sensitivity_offload_penalty,
        "area_risk_offload_penalty": config.area_risk_offload_penalty,
        "edge_delay_scale": config.edge_delay_scale,
        "cloud_backhaul_delay_per_task": config.cloud_backhaul_delay_per_task,
        "cloud_compute_delay_per_task": config.cloud_compute_delay_per_task,
        "cloud_delay_scale": config.cloud_delay_scale,
        "cloud_usage_penalty_per_task": config.cloud_usage_penalty_per_task,
        "low_link_cloud_penalty_per_task": config.low_link_cloud_penalty_per_task,
        "low_link_cloud_penalty_threshold": config.low_link_cloud_penalty_threshold,
        "edge_congestion_penalty_per_task": config.edge_congestion_penalty_per_task,
        "edge_congestion_threshold": config.edge_congestion_threshold,
        "cloud_congestion_relief_bonus_per_task": config.cloud_congestion_relief_bonus_per_task,
        "cloud_data_sensitivity_multiplier": config.cloud_data_sensitivity_multiplier,
        "cloud_area_risk_multiplier": config.cloud_area_risk_multiplier,
        "battery_energy_per_level_j": config.battery_energy_per_level_j,
        "scenario_defaults": {
            name: {
                "link_probs": list(make_offloading_config_for_coverage(name).link_probs),
                "edge_load_probs": list(make_offloading_config_for_coverage(name).edge_load_probs),
                "cloud_load_probs": list(make_offloading_config_for_coverage(name).cloud_load_probs),
            }
            for name in COVERAGE_SCENARIOS
        },
    }


def _build_key_findings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred_order = (
        "weak_coverage_少云",
        "congested_edge_转云",
        "area_risk_抑制云端卸载",
        "data_sensitivity_抑制云端卸载",
    )
    findings: list[dict[str, Any]] = []
    for name in preferred_order:
        matched = [row for row in rows if row.get("hypothesis") == name]
        if not matched:
            continue
        best = max(matched, key=lambda row: float(row.get("stable_ratio", 0.0)))
        findings.append(
            {
                "hypothesis": name,
                "source": best.get("source", ""),
                "passed": _to_bool(best.get("passed")),
                "stable_ratio": float(best.get("stable_ratio", 0.0)),
                "mean_delta": float(best.get("mean_delta", 0.0)),
                "summary": _finding_summary(name, best),
            }
        )
    return findings


def _finding_summary(name: str, row: dict[str, Any]) -> str:
    passed_text = "通过" if _to_bool(row.get("passed")) else "未通过"
    stable_ratio = float(row.get("stable_ratio", 0.0))
    mean_delta = float(row.get("mean_delta", 0.0))
    return f"{passed_text}，稳定比例 {stable_ratio:.2f}，均值差异 {mean_delta:.4f}。"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: _parse_cell(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def _parse_cell(value: str) -> Any:
    if value == "":
        return ""
    try:
        int_value = int(value)
    except ValueError:
        int_value = None
    if int_value is not None and str(int_value) == value:
        return int_value
    try:
        return float(value)
    except ValueError:
        return value


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "passed"}
