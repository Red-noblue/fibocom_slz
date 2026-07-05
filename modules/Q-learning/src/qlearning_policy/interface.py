# 中文说明：本文件定义 Q-learning 策略模块对外暴露的状态、动作和决策接口。
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .offloading import OffloadingAction, OffloadingConfig, OffloadingEnv, OffloadingState
from .policies import RuleBasedOffloadingPolicy
from .scenarios import make_offloading_config_for_coverage


INTERFACE_SCHEMA_VERSION = "qlearning_policy.interface.v1"


@dataclass(frozen=True)
class PolicyStatePayload:
    """模块间传递的离散策略状态。"""

    queue: int
    link: int
    battery: int
    edge_load: int
    cloud_load: int = 1
    task_urgency: int = 1
    data_sensitivity: int = 1
    area_risk: int = 1

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "PolicyStatePayload":
        return cls(
            queue=_to_int(payload.get("queue"), "queue"),
            link=_to_int(payload.get("link"), "link"),
            battery=_to_int(payload.get("battery"), "battery"),
            edge_load=_to_int(payload.get("edge_load"), "edge_load"),
            cloud_load=_to_int(payload.get("cloud_load", 1), "cloud_load"),
            task_urgency=_to_int(payload.get("task_urgency", 1), "task_urgency"),
            data_sensitivity=_to_int(payload.get("data_sensitivity", 1), "data_sensitivity"),
            area_risk=_to_int(payload.get("area_risk", 1), "area_risk"),
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "queue": self.queue,
            "link": self.link,
            "battery": self.battery,
            "edge_load": self.edge_load,
            "cloud_load": self.cloud_load,
            "task_urgency": self.task_urgency,
            "data_sensitivity": self.data_sensitivity,
            "area_risk": self.area_risk,
        }

    def to_offloading_state(self, config: OffloadingConfig) -> OffloadingState:
        _validate_closed_range(self.queue, 0, config.queue_capacity, "queue")
        _validate_index(self.link, len(config.link_rates_bps), "link")
        _validate_index(self.battery, config.battery_level_count, "battery")
        _validate_index(self.edge_load, len(config.edge_load_levels), "edge_load")
        _validate_index(self.cloud_load, len(config.cloud_load_levels), "cloud_load")
        _validate_index(self.task_urgency, len(config.task_urgency_probs), "task_urgency")
        _validate_index(self.data_sensitivity, len(config.data_sensitivity_probs), "data_sensitivity")
        _validate_index(self.area_risk, len(config.area_risk_probs), "area_risk")
        return OffloadingState(
            queue=self.queue,
            link=self.link,
            battery=self.battery,
            edge_load=self.edge_load,
            cloud_load=self.cloud_load,
            task_urgency=self.task_urgency,
            data_sensitivity=self.data_sensitivity,
            area_risk=self.area_risk,
        )


@dataclass(frozen=True)
class PolicyActionPayload:
    """对外动作命名使用 edge_tasks，避免把边缘卸载和云端卸载混在一起。"""

    local_tasks: int
    edge_tasks: int
    cloud_tasks: int

    @classmethod
    def from_action(cls, action: OffloadingAction) -> "PolicyActionPayload":
        return cls(
            local_tasks=action.local_tasks,
            edge_tasks=action.offload_tasks,
            cloud_tasks=action.cloud_tasks,
        )

    @property
    def processed_tasks(self) -> int:
        return self.local_tasks + self.edge_tasks + self.cloud_tasks

    @property
    def remote_tasks(self) -> int:
        return self.edge_tasks + self.cloud_tasks

    def as_dict(self) -> dict[str, int]:
        return {
            "local_tasks": self.local_tasks,
            "edge_tasks": self.edge_tasks,
            "cloud_tasks": self.cloud_tasks,
            "processed_tasks": self.processed_tasks,
            "remote_tasks": self.remote_tasks,
        }


@dataclass(frozen=True)
class PolicyDecisionPayload:
    """对外决策结果，包含动作、估算代价和可解释提示。"""

    schema_version: str
    scenario_name: str
    decision_source: str
    state: PolicyStatePayload
    action: PolicyActionPayload
    action_class: str
    estimated_reward: float
    estimated_delay: float
    estimated_energy: float
    q_value: float | None = None
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scenario_name": self.scenario_name,
            "decision_source": self.decision_source,
            "state": self.state.as_dict(),
            "action": self.action.as_dict(),
            "action_class": self.action_class,
            "estimated_reward": self.estimated_reward,
            "estimated_delay": self.estimated_delay,
            "estimated_energy": self.estimated_energy,
            "q_value": self.q_value,
            "notes": list(self.notes),
        }


def build_interface_contract(config: OffloadingConfig | None = None) -> dict[str, Any]:
    """返回模块对外接口说明，供其他模块或前端读取。"""

    active_config = config or OffloadingConfig()
    return {
        "schema_version": INTERFACE_SCHEMA_VERSION,
        "module_role": "低空无人机端-边-云计算卸载策略决策层",
        "state_fields": [
            {
                "name": "queue",
                "type": "int",
                "range": [0, active_config.queue_capacity],
                "source_hint": "任务队列长度，可由任务调度或虚拟验证模块给出",
            },
            {
                "name": "link",
                "type": "int",
                "range": [0, len(active_config.link_rates_bps) - 1],
                "source_hint": "链路质量等级，可由无线地图/网络覆盖模块离散化得到",
            },
            {
                "name": "battery",
                "type": "int",
                "range": [0, active_config.battery_level_count - 1],
                "source_hint": "电量等级，可由天气能耗模块或仿真状态给出",
            },
            {
                "name": "edge_load",
                "type": "int",
                "range": [0, len(active_config.edge_load_levels) - 1],
                "source_hint": "边缘节点负载等级，可由 MEC/基站侧状态给出",
            },
            {
                "name": "cloud_load",
                "type": "int",
                "range": [0, len(active_config.cloud_load_levels) - 1],
                "source_hint": "云端负载等级，可由云侧状态或实验场景给出",
            },
            {
                "name": "task_urgency",
                "type": "int",
                "range": [0, len(active_config.task_urgency_probs) - 1],
                "source_hint": "任务紧急度，越高越看重 deadline 惩罚",
            },
            {
                "name": "data_sensitivity",
                "type": "int",
                "range": [0, len(active_config.data_sensitivity_probs) - 1],
                "source_hint": "数据敏感等级，越高越抑制远端尤其云端卸载",
            },
            {
                "name": "area_risk",
                "type": "int",
                "range": [0, len(active_config.area_risk_probs) - 1],
                "source_hint": "区域风险等级，越高越抑制云端卸载",
            },
        ],
        "action_fields": [
            {"name": "local_tasks", "type": "int", "meaning": "本机处理任务数"},
            {"name": "edge_tasks", "type": "int", "meaning": "边缘侧处理任务数"},
            {"name": "cloud_tasks", "type": "int", "meaning": "云端处理任务数"},
        ],
        "decision_modes": [
            {"name": "policy_table", "meaning": "读取训练后的 policy_table.csv 进行精确状态查表"},
            {"name": "rule_based", "meaning": "无训练表时使用可解释规则基线"},
        ],
        "integration_boundary": {
            "input_side": ["无线地图/网络覆盖", "天气能耗", "虚拟验证", "任务调度"],
            "output_side": ["本地计算", "边缘卸载", "云端卸载", "延迟/降级处理"],
            "current_scope": "本接口只定义策略决策输入输出，不直接修改外部模块或运行环境。",
        },
    }


def decide_policy(
    state_payload: PolicyStatePayload,
    *,
    scenario_name: str = "balanced",
    policy_table_path: Path | None = None,
) -> PolicyDecisionPayload:
    """根据输入状态输出动作；有训练表则查表，否则走规则基线。"""

    config = make_offloading_config_for_coverage(scenario_name)
    env = OffloadingEnv(config=config)
    state = state_payload.to_offloading_state(config)
    if policy_table_path is not None:
        action, q_value = _lookup_policy_table_action(policy_table_path, state_payload)
        return _build_decision(
            scenario_name=scenario_name,
            decision_source="policy_table",
            env=env,
            state_payload=state_payload,
            state=state,
            action=action,
            q_value=q_value,
        )

    action = RuleBasedOffloadingPolicy().select_action(state, env)
    return _build_decision(
        scenario_name=scenario_name,
        decision_source="rule_based",
        env=env,
        state_payload=state_payload,
        state=state,
        action=action,
        q_value=None,
    )


def _lookup_policy_table_action(policy_table_path: Path, state_payload: PolicyStatePayload) -> tuple[OffloadingAction, float | None]:
    if not policy_table_path.is_file():
        raise FileNotFoundError(f"policy table not found: {policy_table_path}")

    with policy_table_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if _policy_row_matches_state(row, state_payload):
                return (
                    OffloadingAction(
                        local_tasks=_to_int(row.get("local_tasks"), "local_tasks"),
                        offload_tasks=_to_int(row.get("offload_tasks", row.get("edge_tasks")), "offload_tasks"),
                        cloud_tasks=_to_int(row.get("cloud_tasks", 0), "cloud_tasks"),
                    ),
                    _to_optional_float(row.get("q_value")),
                )
    raise ValueError(f"policy table has no exact row for state: {state_payload.as_dict()}")


def _policy_row_matches_state(row: dict[str, str], state_payload: PolicyStatePayload) -> bool:
    for field_name, expected_value in state_payload.as_dict().items():
        if field_name not in row:
            return False
        if _to_int(row[field_name], field_name) != expected_value:
            return False
    return True


def _build_decision(
    *,
    scenario_name: str,
    decision_source: str,
    env: OffloadingEnv,
    state_payload: PolicyStatePayload,
    state: OffloadingState,
    action: OffloadingAction,
    q_value: float | None,
) -> PolicyDecisionPayload:
    breakdown = env.compute_reward(state, action)
    public_action = PolicyActionPayload.from_action(action)
    return PolicyDecisionPayload(
        schema_version=INTERFACE_SCHEMA_VERSION,
        scenario_name=scenario_name,
        decision_source=decision_source,
        state=state_payload,
        action=public_action,
        action_class=_classify_action(public_action),
        estimated_reward=float(breakdown.reward),
        estimated_delay=float(breakdown.delay),
        estimated_energy=float(breakdown.energy),
        q_value=q_value,
        notes=_build_decision_notes(env.config, state, action),
    )


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


def _build_decision_notes(config: OffloadingConfig, state: OffloadingState, action: OffloadingAction) -> tuple[str, ...]:
    notes: list[str] = []
    if state.link <= config.low_link_cloud_penalty_threshold and action.cloud_tasks > 0:
        notes.append("当前链路较弱但仍选择云端，应检查 reward 或上游链路估计。")
    if state.edge_load >= config.edge_congestion_threshold and action.offload_tasks > 0:
        notes.append("边缘负载较高但仍选择边缘，应检查是否存在本地/云端约束。")
    if state.area_risk >= 2 and action.cloud_tasks > 0:
        notes.append("高风险区域仍选择云端，应检查 area_risk 语义是否符合任务安全要求。")
    if state.data_sensitivity >= 2 and action.cloud_tasks > 0:
        notes.append("高敏感数据仍选择云端，应检查数据治理或脱敏条件。")
    return tuple(notes)


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _to_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _validate_index(value: int, upper_bound: int, field_name: str) -> None:
    if not 0 <= value < upper_bound:
        raise ValueError(f"{field_name} out of range: {value}")


def _validate_closed_range(value: int, lower_bound: int, upper_bound: int, field_name: str) -> None:
    if not lower_bound <= value <= upper_bound:
        raise ValueError(f"{field_name} out of range: {value}")
