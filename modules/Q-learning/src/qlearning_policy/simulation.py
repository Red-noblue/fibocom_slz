# 中文说明：本文件组织训练、评估和基础策略对比实验。
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from .agent import QLearningAgent, QLearningParams
from .offloading import OffloadingAction, OffloadingConfig, OffloadingEnv
from .policies import CloudOnlyPolicy, LocalOnlyPolicy, OffloadOnlyPolicy, Policy, RuleBasedOffloadingPolicy


@dataclass(frozen=True)
class EpisodeMetrics:
    average_reward: float
    average_delay: float
    average_energy: float
    average_queue: float
    processed_tasks: int
    offload_ratio: float
    edge_offload_ratio: float
    cloud_offload_ratio: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "average_reward": self.average_reward,
            "average_delay": self.average_delay,
            "average_energy": self.average_energy,
            "average_queue": self.average_queue,
            "processed_tasks": self.processed_tasks,
            "offload_ratio": self.offload_ratio,
            "edge_offload_ratio": self.edge_offload_ratio,
            "cloud_offload_ratio": self.cloud_offload_ratio,
        }


@dataclass(frozen=True)
class DecisionTraceRow:
    slot: int
    state_index: int
    queue: int
    link: int
    battery: int
    edge_load: int
    cloud_load: int
    task_urgency: int
    data_sensitivity: int
    area_risk: int
    action_index: int
    requested_local_tasks: int
    requested_offload_tasks: int
    requested_cloud_tasks: int
    executed_local_tasks: int
    executed_offload_tasks: int
    executed_cloud_tasks: int
    arrival: int
    reward: float
    utility: float
    delay: float
    energy: float
    queue_penalty: float
    illegal_penalty: float
    low_link_offload_penalty: float
    urgency_delay_penalty: float
    deadline_miss_penalty: float
    data_sensitivity_penalty: float
    area_risk_penalty: float
    cloud_usage_penalty: float
    low_link_cloud_penalty: float
    edge_congestion_penalty: float
    cloud_congestion_relief_bonus: float
    next_queue: int
    next_link: int
    next_battery: int
    next_edge_load: int
    next_cloud_load: int
    next_task_urgency: int
    next_data_sensitivity: int
    next_area_risk: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "slot": self.slot,
            "state_index": self.state_index,
            "queue": self.queue,
            "link": self.link,
            "battery": self.battery,
            "edge_load": self.edge_load,
            "cloud_load": self.cloud_load,
            "task_urgency": self.task_urgency,
            "data_sensitivity": self.data_sensitivity,
            "area_risk": self.area_risk,
            "action_index": self.action_index,
            "requested_local_tasks": self.requested_local_tasks,
            "requested_offload_tasks": self.requested_offload_tasks,
            "requested_cloud_tasks": self.requested_cloud_tasks,
            "executed_local_tasks": self.executed_local_tasks,
            "executed_offload_tasks": self.executed_offload_tasks,
            "executed_cloud_tasks": self.executed_cloud_tasks,
            "arrival": self.arrival,
            "reward": self.reward,
            "utility": self.utility,
            "delay": self.delay,
            "energy": self.energy,
            "queue_penalty": self.queue_penalty,
            "illegal_penalty": self.illegal_penalty,
            "low_link_offload_penalty": self.low_link_offload_penalty,
            "urgency_delay_penalty": self.urgency_delay_penalty,
            "deadline_miss_penalty": self.deadline_miss_penalty,
            "data_sensitivity_penalty": self.data_sensitivity_penalty,
            "area_risk_penalty": self.area_risk_penalty,
            "cloud_usage_penalty": self.cloud_usage_penalty,
            "low_link_cloud_penalty": self.low_link_cloud_penalty,
            "edge_congestion_penalty": self.edge_congestion_penalty,
            "cloud_congestion_relief_bonus": self.cloud_congestion_relief_bonus,
            "next_queue": self.next_queue,
            "next_link": self.next_link,
            "next_battery": self.next_battery,
            "next_edge_load": self.next_edge_load,
            "next_cloud_load": self.next_cloud_load,
            "next_task_urgency": self.next_task_urgency,
            "next_data_sensitivity": self.next_data_sensitivity,
            "next_area_risk": self.next_area_risk,
        }


@dataclass(frozen=True)
class TrainingResult:
    config: OffloadingConfig
    agent: QLearningAgent
    metrics: EpisodeMetrics
    rewards: np.ndarray
    average_rewards: np.ndarray
    actions: tuple[OffloadingAction, ...]
    decision_trace: tuple[DecisionTraceRow, ...]


@dataclass(frozen=True)
class StrategySuiteResult:
    q_learning: TrainingResult
    metrics_by_strategy: Mapping[str, EpisodeMetrics]


def train_q_learning(
    config: OffloadingConfig | None = None,
    params: QLearningParams | None = None,
    *,
    slots: int = 3000,
    seed: int = 0,
) -> TrainingResult:
    if slots <= 0:
        raise ValueError("slots must be positive")

    env = OffloadingEnv(config=config, seed=seed)
    agent = QLearningAgent(
        state_count=env.codec.size,
        action_count=len(env.actions),
        params=params or QLearningParams(),
        seed=seed + 101,
    )
    state = env.reset(seed=seed)

    rewards = np.zeros(slots, dtype=np.float64)
    average_rewards = np.zeros(slots, dtype=np.float64)
    delays = np.zeros(slots, dtype=np.float64)
    energies = np.zeros(slots, dtype=np.float64)
    queues = np.zeros(slots, dtype=np.float64)
    processed_total = 0
    edge_offloaded_total = 0
    cloud_offloaded_total = 0
    trace_rows: list[DecisionTraceRow] = []

    for slot in range(slots):
        state_index = env.encode_state(state)
        action_index = agent.select_action(state_index, explore=True)
        requested_action = env.actions[action_index]
        result = env.step(state, requested_action)
        next_state_index = env.encode_state(result.next_state)
        agent.update(state_index, action_index, result.reward, next_state_index)

        rewards[slot] = result.reward
        average_rewards[slot] = float(np.mean(rewards[: slot + 1]))
        delays[slot] = result.breakdown.delay
        energies[slot] = result.breakdown.energy
        queues[slot] = result.state.queue
        processed_total += result.breakdown.executed_action.processed_tasks
        edge_offloaded_total += result.breakdown.executed_action.offload_tasks
        cloud_offloaded_total += result.breakdown.executed_action.cloud_tasks
        trace_rows.append(
            DecisionTraceRow(
                slot=slot,
                state_index=state_index,
                queue=result.state.queue,
                link=result.state.link,
                battery=result.state.battery,
                edge_load=result.state.edge_load,
                cloud_load=result.state.cloud_load,
                task_urgency=result.state.task_urgency,
                data_sensitivity=result.state.data_sensitivity,
                area_risk=result.state.area_risk,
                action_index=action_index,
                requested_local_tasks=requested_action.local_tasks,
                requested_offload_tasks=requested_action.offload_tasks,
                requested_cloud_tasks=requested_action.cloud_tasks,
                executed_local_tasks=result.breakdown.executed_action.local_tasks,
                executed_offload_tasks=result.breakdown.executed_action.offload_tasks,
                executed_cloud_tasks=result.breakdown.executed_action.cloud_tasks,
                arrival=result.arrival,
                reward=result.reward,
                utility=result.breakdown.utility,
                delay=result.breakdown.delay,
                energy=result.breakdown.energy,
                queue_penalty=result.breakdown.queue_penalty,
                illegal_penalty=result.breakdown.illegal_penalty,
                low_link_offload_penalty=result.breakdown.low_link_offload_penalty,
                urgency_delay_penalty=result.breakdown.urgency_delay_penalty,
                deadline_miss_penalty=result.breakdown.deadline_miss_penalty,
                data_sensitivity_penalty=result.breakdown.data_sensitivity_penalty,
                area_risk_penalty=result.breakdown.area_risk_penalty,
                cloud_usage_penalty=result.breakdown.cloud_usage_penalty,
                low_link_cloud_penalty=result.breakdown.low_link_cloud_penalty,
                edge_congestion_penalty=result.breakdown.edge_congestion_penalty,
                cloud_congestion_relief_bonus=result.breakdown.cloud_congestion_relief_bonus,
                next_queue=result.next_state.queue,
                next_link=result.next_state.link,
                next_battery=result.next_state.battery,
                next_edge_load=result.next_state.edge_load,
                next_cloud_load=result.next_state.cloud_load,
                next_task_urgency=result.next_state.task_urgency,
                next_data_sensitivity=result.next_state.data_sensitivity,
                next_area_risk=result.next_state.area_risk,
            )
        )
        state = result.next_state

    return TrainingResult(
        config=env.config,
        agent=agent,
        metrics=_build_metrics(
            rewards=rewards,
            delays=delays,
            energies=energies,
            queues=queues,
            processed_total=processed_total,
            edge_offloaded_total=edge_offloaded_total,
            cloud_offloaded_total=cloud_offloaded_total,
        ),
        rewards=rewards,
        average_rewards=average_rewards,
        actions=env.actions,
        decision_trace=tuple(trace_rows),
    )


def evaluate_policy(
    policy: Policy,
    config: OffloadingConfig | None = None,
    *,
    slots: int = 3000,
    seed: int = 0,
) -> EpisodeMetrics:
    if slots <= 0:
        raise ValueError("slots must be positive")

    env = OffloadingEnv(config=config, seed=seed)
    state = env.reset(seed=seed)
    rewards = np.zeros(slots, dtype=np.float64)
    delays = np.zeros(slots, dtype=np.float64)
    energies = np.zeros(slots, dtype=np.float64)
    queues = np.zeros(slots, dtype=np.float64)
    processed_total = 0
    edge_offloaded_total = 0
    cloud_offloaded_total = 0

    for slot in range(slots):
        action = policy.select_action(state, env)
        result = env.step(state, action)
        rewards[slot] = result.reward
        delays[slot] = result.breakdown.delay
        energies[slot] = result.breakdown.energy
        queues[slot] = result.state.queue
        processed_total += result.breakdown.executed_action.processed_tasks
        edge_offloaded_total += result.breakdown.executed_action.offload_tasks
        cloud_offloaded_total += result.breakdown.executed_action.cloud_tasks
        state = result.next_state

    return _build_metrics(
        rewards=rewards,
        delays=delays,
        energies=energies,
        queues=queues,
        processed_total=processed_total,
        edge_offloaded_total=edge_offloaded_total,
        cloud_offloaded_total=cloud_offloaded_total,
    )


def evaluate_trained_q_learning(
    result: TrainingResult,
    *,
    slots: int = 3000,
    seed: int = 0,
) -> EpisodeMetrics:
    """评估训练后的贪心策略，不再使用 epsilon 探索。"""

    if slots <= 0:
        raise ValueError("slots must be positive")

    env = OffloadingEnv(config=result.config, seed=seed)
    state = env.reset(seed=seed)
    rewards = np.zeros(slots, dtype=np.float64)
    delays = np.zeros(slots, dtype=np.float64)
    energies = np.zeros(slots, dtype=np.float64)
    queues = np.zeros(slots, dtype=np.float64)
    processed_total = 0
    edge_offloaded_total = 0
    cloud_offloaded_total = 0

    for slot in range(slots):
        state_index = env.encode_state(state)
        action_index = result.agent.select_action(state_index, explore=False)
        action = env.actions[action_index]
        step_result = env.step(state, action)
        rewards[slot] = step_result.reward
        delays[slot] = step_result.breakdown.delay
        energies[slot] = step_result.breakdown.energy
        queues[slot] = step_result.state.queue
        processed_total += step_result.breakdown.executed_action.processed_tasks
        edge_offloaded_total += step_result.breakdown.executed_action.offload_tasks
        cloud_offloaded_total += step_result.breakdown.executed_action.cloud_tasks
        state = step_result.next_state

    return _build_metrics(
        rewards=rewards,
        delays=delays,
        energies=energies,
        queues=queues,
        processed_total=processed_total,
        edge_offloaded_total=edge_offloaded_total,
        cloud_offloaded_total=cloud_offloaded_total,
    )


def compare_basic_strategies(
    config: OffloadingConfig | None = None,
    params: QLearningParams | None = None,
    *,
    slots: int = 3000,
    seed: int = 0,
) -> Mapping[str, EpisodeMetrics]:
    return run_basic_strategy_suite(config=config, params=params, slots=slots, seed=seed).metrics_by_strategy


def run_basic_strategy_suite(
    config: OffloadingConfig | None = None,
    params: QLearningParams | None = None,
    *,
    slots: int = 3000,
    seed: int = 0,
) -> StrategySuiteResult:
    q_result = train_q_learning(config=config, params=params, slots=slots, seed=seed)
    metrics = {
        "q_learning": q_result.metrics,
        "local_only": evaluate_policy(LocalOnlyPolicy(), config=config, slots=slots, seed=seed),
        "offload_only": evaluate_policy(OffloadOnlyPolicy(), config=config, slots=slots, seed=seed),
        "cloud_only": evaluate_policy(CloudOnlyPolicy(), config=config, slots=slots, seed=seed),
        "rule_based": evaluate_policy(RuleBasedOffloadingPolicy(), config=config, slots=slots, seed=seed),
    }
    return StrategySuiteResult(q_learning=q_result, metrics_by_strategy=metrics)


def build_learning_curve_rows(result: TrainingResult) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for slot, (reward, average_reward) in enumerate(zip(result.rewards, result.average_rewards, strict=True)):
        rows.append(
            {
                "slot": slot,
                "reward": float(reward),
                "average_reward": float(average_reward),
            }
        )
    return rows


def build_decision_trace_rows(result: TrainingResult) -> list[dict[str, float | int]]:
    return [row.as_dict() for row in result.decision_trace]


def build_policy_table_rows(result: TrainingResult) -> list[dict[str, float | int]]:
    env = OffloadingEnv(config=result.config, seed=0)
    rows: list[dict[str, float | int]] = []
    for state_index in range(env.codec.size):
        state = env.decode_state(state_index)
        q_values = result.agent.q_table[state_index]
        action_index = int(np.argmax(q_values))
        action = result.actions[action_index]
        rows.append(
            {
                "state_index": state_index,
                "queue": state.queue,
                "link": state.link,
                "link_rate_bps": float(result.config.link_rates_bps[state.link]),
                "battery": state.battery,
                "edge_load": state.edge_load,
                "edge_load_value": float(result.config.edge_load_levels[state.edge_load]),
                "cloud_load": state.cloud_load,
                "cloud_load_value": float(result.config.cloud_load_levels[state.cloud_load]),
                "task_urgency": state.task_urgency,
                "data_sensitivity": state.data_sensitivity,
                "area_risk": state.area_risk,
                "greedy_action_index": action_index,
                "local_tasks": action.local_tasks,
                "offload_tasks": action.offload_tasks,
                "cloud_tasks": action.cloud_tasks,
                "q_value": float(q_values[action_index]),
            }
        )
    return rows


def _build_metrics(
    *,
    rewards: np.ndarray,
    delays: np.ndarray,
    energies: np.ndarray,
    queues: np.ndarray,
    processed_total: int,
    edge_offloaded_total: int,
    cloud_offloaded_total: int,
) -> EpisodeMetrics:
    offloaded_total = edge_offloaded_total + cloud_offloaded_total
    return EpisodeMetrics(
        average_reward=float(np.mean(rewards)),
        average_delay=float(np.mean(delays)),
        average_energy=float(np.mean(energies)),
        average_queue=float(np.mean(queues)),
        processed_tasks=int(processed_total),
        offload_ratio=float(offloaded_total / processed_total) if processed_total > 0 else 0.0,
        edge_offload_ratio=float(edge_offloaded_total / processed_total) if processed_total > 0 else 0.0,
        cloud_offload_ratio=float(cloud_offloaded_total / processed_total) if processed_total > 0 else 0.0,
    )
