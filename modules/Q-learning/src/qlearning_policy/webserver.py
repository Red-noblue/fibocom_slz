# 中文说明：本文件提供 Q-learning 模块的轻量 Web 服务，统一暴露静态前端和 act/step/rollout API。
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .dashboard import (
    DEFAULT_DASHBOARD_OUTPUT,
    DEFAULT_TRAINED_POLICY_OUTPUT,
    build_dashboard_payload,
    export_dashboard_payload,
    export_trained_policy_snapshot,
)
from .interface import PolicyActionPayload, PolicyStatePayload
from .offloading import OffloadingAction, OffloadingEnv, OffloadingState, StepResult
from .policies import RuleBasedOffloadingPolicy
from .scenarios import list_coverage_scenario_names, make_offloading_config_for_coverage


DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 18081
DEFAULT_POLICY_MODE = "trained_or_rule"
DEFAULT_POLICY_SLOTS = 8000
DEFAULT_POLICY_SEED = 31
SUPPORTED_POLICY_MODES = ("trained_only", "trained_or_rule", "rule_based")


@dataclass(frozen=True)
class TrainedPolicyEntry:
    action: OffloadingAction
    q_value: float
    visit_count: int


@dataclass(frozen=True)
class TrainedPolicyScenarioSummary:
    entry_count: int
    visited_state_count: int
    visited_ratio: float
    sample_states: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class ActionResolution:
    source: str
    action: OffloadingAction | None
    action_class: str | None
    q_value: float | None
    visit_count: int
    covered: bool
    notes: tuple[str, ...]


class TrainedPolicyStore:
    """加载训练快照并提供状态查表能力。"""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.training = payload.get("training", {})
        self.scenario_maps: dict[str, dict[tuple[int, ...], TrainedPolicyEntry]] = {}
        self.scenario_summaries: dict[str, TrainedPolicyScenarioSummary] = {}

        for scenario_name, scenario_payload in payload.get("scenarios", {}).items():
            entries: dict[tuple[int, ...], TrainedPolicyEntry] = {}
            for row in scenario_payload.get("entries", []):
                state_key = tuple(int(value) for value in row[:8])
                entries[state_key] = TrainedPolicyEntry(
                    action=OffloadingAction(
                        local_tasks=int(row[8]),
                        offload_tasks=int(row[9]),
                        cloud_tasks=int(row[10]),
                    ),
                    q_value=float(row[11]),
                    visit_count=int(row[12]),
                )
            self.scenario_maps[scenario_name] = entries
            self.scenario_summaries[scenario_name] = TrainedPolicyScenarioSummary(
                entry_count=int(scenario_payload.get("entry_count", len(entries))),
                visited_state_count=int(scenario_payload.get("visited_state_count", 0)),
                visited_ratio=float(scenario_payload.get("visited_ratio", 0.0)),
                sample_states=tuple(
                    tuple(int(value) for value in sample_row)
                    for sample_row in scenario_payload.get("sample_states", [])
                ),
            )

    @classmethod
    def load(cls, path: Path) -> "TrainedPolicyStore":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def lookup(self, scenario_name: str, state_payload: PolicyStatePayload) -> tuple[TrainedPolicyEntry | None, TrainedPolicyScenarioSummary | None]:
        state_key = _state_key(state_payload)
        return (
            self.scenario_maps.get(scenario_name, {}).get(state_key),
            self.scenario_summaries.get(scenario_name),
        )

    def meta_summary(self) -> dict[str, Any]:
        return {
            "training": self.training,
            "scenarios": {
                name: {
                    "entry_count": summary.entry_count,
                    "visited_state_count": summary.visited_state_count,
                    "visited_ratio": summary.visited_ratio,
                    "sample_states": [list(values) for values in summary.sample_states],
                }
                for name, summary in self.scenario_summaries.items()
            },
        }


def ensure_runtime_artifacts(
    *,
    dashboard_path: Path = DEFAULT_DASHBOARD_OUTPUT,
    trained_policy_path: Path = DEFAULT_TRAINED_POLICY_OUTPUT,
    policy_slots: int = DEFAULT_POLICY_SLOTS,
    policy_seed: int = DEFAULT_POLICY_SEED,
) -> dict[str, str]:
    """确保前端和运行时所需的 JSON 产物存在。"""

    if not dashboard_path.is_file():
        export_dashboard_payload(output_path=dashboard_path)
    if not trained_policy_path.is_file():
        export_trained_policy_snapshot(
            scenario_names=tuple(list_coverage_scenario_names()),
            slots=policy_slots,
            seed=policy_seed,
            output_path=trained_policy_path,
        )
    return {
        "dashboard_json": str(dashboard_path),
        "trained_policy_json": str(trained_policy_path),
    }


def build_meta_payload(
    *,
    dashboard_path: Path = DEFAULT_DASHBOARD_OUTPUT,
    trained_policy_store: TrainedPolicyStore,
) -> dict[str, Any]:
    """返回前端初始化所需的服务元数据。"""

    if dashboard_path.is_file():
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    else:
        dashboard = build_dashboard_payload()
    return {
        "schema_version": "qlearning_policy.api.meta.v1",
        "api_capabilities": ["act", "step", "rollout"],
        "default_policy_mode": DEFAULT_POLICY_MODE,
        "policy_modes": list(SUPPORTED_POLICY_MODES),
        "dashboard": dashboard,
        "trained_policy": trained_policy_store.meta_summary(),
    }


def build_act_response(
    *,
    scenario_name: str,
    state_payload: PolicyStatePayload,
    policy_store: TrainedPolicyStore,
    policy_mode: str = DEFAULT_POLICY_MODE,
) -> dict[str, Any]:
    config = make_offloading_config_for_coverage(scenario_name)
    env = OffloadingEnv(config=config, seed=0)
    state = state_payload.to_offloading_state(config)
    resolution = resolve_action(
        state_payload=state_payload,
        scenario_name=scenario_name,
        env=env,
        state=state,
        policy_store=policy_store,
        policy_mode=policy_mode,
    )
    return {
        "schema_version": "qlearning_policy.api.act.v1",
        "scenario_name": scenario_name,
        "policy_mode": policy_mode,
        "state": state_payload.as_dict(),
        "resolved_decision": _serialize_resolution(resolution, env=env, state=state, scenario_name=scenario_name),
        "coverage": _coverage_payload(policy_store, scenario_name),
    }


def build_step_response(
    *,
    scenario_name: str,
    state_payload: PolicyStatePayload,
    policy_store: TrainedPolicyStore,
    policy_mode: str = DEFAULT_POLICY_MODE,
    seed: int | None = None,
) -> dict[str, Any]:
    config = make_offloading_config_for_coverage(scenario_name)
    runtime_seed = _runtime_seed(seed)
    env = OffloadingEnv(config=config, seed=runtime_seed)
    state = state_payload.to_offloading_state(config)
    resolution = resolve_action(
        state_payload=state_payload,
        scenario_name=scenario_name,
        env=env,
        state=state,
        policy_store=policy_store,
        policy_mode=policy_mode,
    )
    if resolution.action is None:
        return {
            "schema_version": "qlearning_policy.api.step.v1",
            "scenario_name": scenario_name,
            "policy_mode": policy_mode,
            "seed": runtime_seed,
            "state": state_payload.as_dict(),
            "resolved_decision": _serialize_resolution(resolution, env=env, state=state, scenario_name=scenario_name),
            "step_result": None,
            "coverage": _coverage_payload(policy_store, scenario_name),
        }

    step_result = env.step(state, resolution.action)
    return {
        "schema_version": "qlearning_policy.api.step.v1",
        "scenario_name": scenario_name,
        "policy_mode": policy_mode,
        "seed": runtime_seed,
        "state": state_payload.as_dict(),
        "resolved_decision": _serialize_resolution(resolution, env=env, state=state, scenario_name=scenario_name),
        "step_result": _serialize_step_result(step_result),
        "coverage": _coverage_payload(policy_store, scenario_name),
    }


def build_rollout_response(
    *,
    scenario_name: str,
    initial_state_payload: PolicyStatePayload,
    policy_store: TrainedPolicyStore,
    steps: int,
    policy_mode: str = DEFAULT_POLICY_MODE,
    seed: int | None = None,
) -> dict[str, Any]:
    if steps <= 0:
        raise ValueError("steps must be positive")

    config = make_offloading_config_for_coverage(scenario_name)
    runtime_seed = _runtime_seed(seed)
    env = OffloadingEnv(config=config, seed=runtime_seed)
    state = initial_state_payload.to_offloading_state(config)

    trace: list[dict[str, Any]] = []
    source_counts = {"trained_policy": 0, "rule_based_fallback": 0, "rule_based": 0, "uncovered_state": 0}
    total_reward = 0.0
    total_processed = 0

    for step_index in range(steps):
        current_payload = PolicyStatePayload(
            queue=state.queue,
            link=state.link,
            battery=state.battery,
            edge_load=state.edge_load,
            cloud_load=state.cloud_load,
            task_urgency=state.task_urgency,
            data_sensitivity=state.data_sensitivity,
            area_risk=state.area_risk,
        )
        resolution = resolve_action(
            state_payload=current_payload,
            scenario_name=scenario_name,
            env=env,
            state=state,
            policy_store=policy_store,
            policy_mode=policy_mode,
        )
        if resolution.source in source_counts:
            source_counts[resolution.source] += 1
        if resolution.action is None:
            trace.append(
                {
                    "step": step_index,
                    "state": current_payload.as_dict(),
                    "resolved_decision": _serialize_resolution(
                        resolution,
                        env=env,
                        state=state,
                        scenario_name=scenario_name,
                    ),
                    "step_result": None,
                }
            )
            break

        step_result = env.step(state, resolution.action)
        total_reward += step_result.reward
        total_processed += step_result.breakdown.executed_action.processed_tasks
        trace.append(
            {
                "step": step_index,
                "state": current_payload.as_dict(),
                "resolved_decision": _serialize_resolution(
                    resolution,
                    env=env,
                    state=state,
                    scenario_name=scenario_name,
                ),
                "step_result": _serialize_step_result(step_result),
            }
        )
        state = step_result.next_state

    final_payload = PolicyStatePayload(
        queue=state.queue,
        link=state.link,
        battery=state.battery,
        edge_load=state.edge_load,
        cloud_load=state.cloud_load,
        task_urgency=state.task_urgency,
        data_sensitivity=state.data_sensitivity,
        area_risk=state.area_risk,
    )
    return {
        "schema_version": "qlearning_policy.api.rollout.v1",
        "scenario_name": scenario_name,
        "policy_mode": policy_mode,
        "seed": runtime_seed,
        "initial_state": initial_state_payload.as_dict(),
        "summary": {
            "steps_requested": steps,
            "steps_executed": len([row for row in trace if row["step_result"] is not None]),
            "average_reward": total_reward / len([row for row in trace if row["step_result"] is not None])
            if any(row["step_result"] is not None for row in trace)
            else 0.0,
            "total_reward": total_reward,
            "total_processed_tasks": total_processed,
            "source_counts": source_counts,
            "final_state": final_payload.as_dict(),
        },
        "trace": trace,
        "coverage": _coverage_payload(policy_store, scenario_name),
    }


def resolve_action(
    *,
    state_payload: PolicyStatePayload,
    scenario_name: str,
    env: OffloadingEnv,
    state: OffloadingState,
    policy_store: TrainedPolicyStore,
    policy_mode: str,
) -> ActionResolution:
    if policy_mode not in SUPPORTED_POLICY_MODES:
        raise ValueError(f"unsupported policy_mode: {policy_mode}")

    policy_entry, _ = policy_store.lookup(scenario_name, state_payload)
    if policy_entry is not None and policy_entry.visit_count > 0 and policy_mode in {"trained_only", "trained_or_rule"}:
        action_payload = PolicyActionPayload.from_action(policy_entry.action)
        return ActionResolution(
            source="trained_policy",
            action=policy_entry.action,
            action_class=_classify_action(action_payload),
            q_value=policy_entry.q_value,
            visit_count=policy_entry.visit_count,
            covered=True,
            notes=(),
        )

    if policy_mode == "trained_only":
        return ActionResolution(
            source="uncovered_state",
            action=None,
            action_class=None,
            q_value=policy_entry.q_value if policy_entry is not None else None,
            visit_count=policy_entry.visit_count if policy_entry is not None else 0,
            covered=False,
            notes=("当前状态未被训练覆盖，trained_only 模式不返回回退动作。",),
        )

    fallback_action = RuleBasedOffloadingPolicy().select_action(state, env)
    return ActionResolution(
        source="rule_based" if policy_mode == "rule_based" else "rule_based_fallback",
        action=fallback_action,
        action_class=_classify_action(PolicyActionPayload.from_action(fallback_action)),
        q_value=policy_entry.q_value if policy_entry is not None else None,
        visit_count=policy_entry.visit_count if policy_entry is not None else 0,
        covered=False,
        notes=("当前状态未被训练覆盖，返回规则策略回退动作。",)
        if policy_mode == "trained_or_rule"
        else (),
    )


def run_web_server(
    *,
    host: str = DEFAULT_WEB_HOST,
    port: int = DEFAULT_WEB_PORT,
    static_dir: Path,
    dashboard_path: Path,
    trained_policy_path: Path,
    policy_slots: int = DEFAULT_POLICY_SLOTS,
    policy_seed: int = DEFAULT_POLICY_SEED,
) -> None:
    ensure_runtime_artifacts(
        dashboard_path=dashboard_path,
        trained_policy_path=trained_policy_path,
        policy_slots=policy_slots,
        policy_seed=policy_seed,
    )
    policy_store = TrainedPolicyStore.load(trained_policy_path)
    meta_payload = build_meta_payload(dashboard_path=dashboard_path, trained_policy_store=policy_store)
    handler = partial(
        QLearningWebHandler,
        static_dir=static_dir,
        policy_store=policy_store,
        meta_payload=meta_payload,
    )
    server = ThreadingHTTPServer((host, port), handler)
    print(
        json.dumps(
            {
                "host": host,
                "port": port,
                "static_dir": str(static_dir),
                "dashboard_json": str(dashboard_path),
                "trained_policy_json": str(trained_policy_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    server.serve_forever()


class QLearningWebHandler(SimpleHTTPRequestHandler):
    """静态前端和 API 共用的请求处理器。"""

    def __init__(
        self,
        *args: Any,
        static_dir: Path,
        policy_store: TrainedPolicyStore,
        meta_payload: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        self.policy_store = policy_store
        self.meta_payload = meta_payload
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._write_json({"status": "ok"})
            return
        if parsed.path == "/api/meta":
            self._write_json(self.meta_payload)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json_body()
            if parsed.path == "/api/act":
                response = build_act_response(
                    scenario_name=_read_scenario_name(payload),
                    state_payload=PolicyStatePayload.from_mapping(payload.get("state", {})),
                    policy_store=self.policy_store,
                    policy_mode=_read_policy_mode(payload),
                )
                self._write_json(response)
                return
            if parsed.path == "/api/step":
                response = build_step_response(
                    scenario_name=_read_scenario_name(payload),
                    state_payload=PolicyStatePayload.from_mapping(payload.get("state", {})),
                    policy_store=self.policy_store,
                    policy_mode=_read_policy_mode(payload),
                    seed=_read_optional_int(payload.get("seed")),
                )
                self._write_json(response)
                return
            if parsed.path == "/api/rollout":
                response = build_rollout_response(
                    scenario_name=_read_scenario_name(payload),
                    initial_state_payload=PolicyStatePayload.from_mapping(payload.get("state", {})),
                    policy_store=self.policy_store,
                    policy_mode=_read_policy_mode(payload),
                    steps=int(payload.get("steps", 8)),
                    seed=_read_optional_int(payload.get("seed")),
                )
                self._write_json(response)
                return
        except FileNotFoundError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
            return
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json({"error": f"unknown API path: {parsed.path}"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        # 保持终端输出简洁，只打印请求核心信息。
        super().log_message(format, *args)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def _write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def _serialize_resolution(
    resolution: ActionResolution,
    *,
    env: OffloadingEnv,
    state: OffloadingState,
    scenario_name: str,
) -> dict[str, Any]:
    if resolution.action is None:
        return {
            "scenario_name": scenario_name,
            "source": resolution.source,
            "covered": resolution.covered,
            "visit_count": resolution.visit_count,
            "q_value": resolution.q_value,
            "action": None,
            "action_class": resolution.action_class,
            "estimated_reward": None,
            "estimated_delay": None,
            "estimated_energy": None,
            "reward_breakdown": None,
            "notes": list(resolution.notes),
        }

    breakdown = env.compute_reward(state, resolution.action)
    action_payload = PolicyActionPayload.from_action(resolution.action)
    return {
        "scenario_name": scenario_name,
        "source": resolution.source,
        "covered": resolution.covered,
        "visit_count": resolution.visit_count,
        "q_value": resolution.q_value,
        "action": action_payload.as_dict(),
        "action_class": resolution.action_class,
        "estimated_reward": breakdown.reward,
        "estimated_delay": breakdown.delay,
        "estimated_energy": breakdown.energy,
        "reward_breakdown": {
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
        },
        "notes": list(resolution.notes),
    }


def _serialize_step_result(step_result: StepResult) -> dict[str, Any]:
    action_payload = PolicyActionPayload.from_action(step_result.breakdown.executed_action)
    return {
        "current_state": step_result.state.as_mapping(),
        "action": action_payload.as_dict(),
        "reward": step_result.reward,
        "arrival": step_result.arrival,
        "next_state": step_result.next_state.as_mapping(),
        "reward_breakdown": {
            "reward": step_result.breakdown.reward,
            "utility": step_result.breakdown.utility,
            "delay": step_result.breakdown.delay,
            "energy": step_result.breakdown.energy,
            "queue_penalty": step_result.breakdown.queue_penalty,
            "illegal_penalty": step_result.breakdown.illegal_penalty,
            "low_link_offload_penalty": step_result.breakdown.low_link_offload_penalty,
            "urgency_delay_penalty": step_result.breakdown.urgency_delay_penalty,
            "deadline_miss_penalty": step_result.breakdown.deadline_miss_penalty,
            "data_sensitivity_penalty": step_result.breakdown.data_sensitivity_penalty,
            "area_risk_penalty": step_result.breakdown.area_risk_penalty,
            "cloud_usage_penalty": step_result.breakdown.cloud_usage_penalty,
            "low_link_cloud_penalty": step_result.breakdown.low_link_cloud_penalty,
            "edge_congestion_penalty": step_result.breakdown.edge_congestion_penalty,
            "cloud_congestion_relief_bonus": step_result.breakdown.cloud_congestion_relief_bonus,
        },
    }


def _coverage_payload(policy_store: TrainedPolicyStore, scenario_name: str) -> dict[str, Any]:
    summary = policy_store.scenario_summaries.get(scenario_name)
    if summary is None:
        return {}
    return {
        "entry_count": summary.entry_count,
        "visited_state_count": summary.visited_state_count,
        "visited_ratio": summary.visited_ratio,
        "sample_states": [list(values) for values in summary.sample_states],
        "training": policy_store.training,
    }


def _classify_action(action: PolicyActionPayload) -> str:
    if action.processed_tasks == 0:
        return "defer"
    active_parts = sum(1 for value in (action.local_tasks, action.edge_tasks, action.cloud_tasks) if value > 0)
    if active_parts > 1:
        return "hybrid"
    if action.local_tasks > 0:
        return "local_only"
    if action.edge_tasks > 0:
        return "edge_only"
    return "cloud_only"


def _runtime_seed(seed: int | None) -> int:
    return seed if seed is not None else secrets.randbelow(2**31 - 1)


def _state_key(state_payload: PolicyStatePayload) -> tuple[int, ...]:
    return (
        state_payload.queue,
        state_payload.link,
        state_payload.battery,
        state_payload.edge_load,
        state_payload.cloud_load,
        state_payload.task_urgency,
        state_payload.data_sensitivity,
        state_payload.area_risk,
    )


def _read_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _read_policy_mode(payload: dict[str, Any]) -> str:
    return str(payload.get("policy_mode", DEFAULT_POLICY_MODE))


def _read_scenario_name(payload: dict[str, Any]) -> str:
    return str(payload.get("scenario_name", "balanced"))
