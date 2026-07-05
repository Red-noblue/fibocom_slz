# 中文说明：本文件定义无人机端边计算卸载的离散仿真环境。
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import ceil

import numpy as np

from .state import StateCodec


@dataclass(frozen=True)
class OffloadingAction:
    """动作：本地、边缘和云端分别处理的任务数。"""

    local_tasks: int
    offload_tasks: int
    cloud_tasks: int = 0

    @property
    def processed_tasks(self) -> int:
        return self.local_tasks + self.offload_tasks + self.cloud_tasks

    @property
    def remote_tasks(self) -> int:
        return self.offload_tasks + self.cloud_tasks


@dataclass(frozen=True)
class OffloadingState:
    """状态：队列、链路、电量、端边云负载和低空任务语义。"""

    queue: int
    link: int
    battery: int
    edge_load: int
    task_urgency: int
    data_sensitivity: int
    area_risk: int
    cloud_load: int = 1

    def as_mapping(self) -> dict[str, int]:
        return {
            "queue": self.queue,
            "link": self.link,
            "battery": self.battery,
            "edge_load": self.edge_load,
            "task_urgency": self.task_urgency,
            "data_sensitivity": self.data_sensitivity,
            "area_risk": self.area_risk,
            "cloud_load": self.cloud_load,
        }


@dataclass(frozen=True)
class RewardBreakdown:
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
    executed_action: OffloadingAction


@dataclass(frozen=True)
class StepResult:
    state: OffloadingState
    action: OffloadingAction
    reward: float
    breakdown: RewardBreakdown
    next_state: OffloadingState
    arrival: int


@dataclass(frozen=True)
class OffloadingConfig:
    """计算卸载环境配置，保持离散状态，方便表格型 Q-learning 起步。"""

    queue_capacity: int = 16
    max_local_tasks: int = 2
    max_offload_tasks: int = 2
    max_cloud_tasks: int = 2
    link_rates_bps: tuple[float, ...] = (2e7, 1e8, 1.5e8)
    link_probs: tuple[float, ...] = (0.25, 0.50, 0.25)
    edge_load_levels: tuple[float, ...] = (0.15, 0.50, 0.85)
    edge_load_probs: tuple[float, ...] = (0.30, 0.50, 0.20)
    cloud_load_levels: tuple[float, ...] = (0.20, 0.55, 0.85)
    cloud_load_probs: tuple[float, ...] = (0.35, 0.45, 0.20)
    battery_level_count: int = 5
    initial_queue: int = 0
    initial_link: int = 2
    initial_battery: int = 4
    initial_edge_load: int = 1
    initial_cloud_load: int = 1
    initial_task_urgency: int = 1
    initial_data_sensitivity: int = 1
    initial_area_risk: int = 1
    arrival_values: tuple[int, ...] = (0, 4, 8)
    arrival_probs: tuple[float, ...] = (0.30, 0.40, 0.30)
    task_urgency_probs: tuple[float, ...] = (0.40, 0.40, 0.20)
    data_sensitivity_probs: tuple[float, ...] = (0.50, 0.35, 0.15)
    area_risk_probs: tuple[float, ...] = (0.55, 0.30, 0.15)
    avg_arrival_rate: float = 4.0
    task_size_bits: float = 3e7
    cycles_per_task: float = 1.3e9
    local_cpu_hz: float = 1.0e9
    beta: float = 8e-27
    tx_power_watts: float = 10.0
    theta: float = 30.0
    delay_weight: float = 1.0
    energy_weight: float = 0.12
    queue_weight: float = 0.2
    illegal_action_penalty: float = 8.0
    low_link_offload_penalty: float = 0.0
    low_link_penalty_threshold: int = 0
    urgency_delay_weight: float = 0.6
    task_deadlines: tuple[float, ...] = (8.0, 6.0, 4.5)
    deadline_miss_penalty: float = 12.0
    data_sensitivity_offload_penalty: float = 3.0
    area_risk_offload_penalty: float = 2.0
    edge_delay_scale: float = 1.5
    cloud_backhaul_delay_per_task: float = 0.8
    cloud_compute_delay_per_task: float = 0.35
    cloud_delay_scale: float = 0.8
    cloud_usage_penalty_per_task: float = 0.6
    low_link_cloud_penalty_per_task: float = 8.0
    low_link_cloud_penalty_threshold: int = 0
    edge_congestion_penalty_per_task: float = 6.0
    edge_congestion_threshold: int = 2
    cloud_congestion_relief_bonus_per_task: float = 10.0
    cloud_data_sensitivity_multiplier: float = 2.5
    cloud_area_risk_multiplier: float = 5.0
    battery_energy_per_level_j: float = 35.0

    def validate(self) -> None:
        if self.queue_capacity < 0:
            raise ValueError("queue_capacity must be non-negative")
        if self.max_local_tasks < 0 or self.max_offload_tasks < 0 or self.max_cloud_tasks < 0:
            raise ValueError("max task counts must be non-negative")
        if self.battery_level_count <= 0:
            raise ValueError("battery_level_count must be positive")
        if not 0 <= self.initial_queue <= self.queue_capacity:
            raise ValueError("initial_queue outside queue range")
        if not 0 <= self.initial_link < len(self.link_rates_bps):
            raise ValueError("initial_link outside link range")
        if not 0 <= self.initial_battery < self.battery_level_count:
            raise ValueError("initial_battery outside battery range")
        if not 0 <= self.initial_edge_load < len(self.edge_load_levels):
            raise ValueError("initial_edge_load outside edge load range")
        if not 0 <= self.initial_cloud_load < len(self.cloud_load_levels):
            raise ValueError("initial_cloud_load outside cloud load range")
        if not 0 <= self.initial_task_urgency < len(self.task_urgency_probs):
            raise ValueError("initial_task_urgency outside task urgency range")
        if not 0 <= self.initial_data_sensitivity < len(self.data_sensitivity_probs):
            raise ValueError("initial_data_sensitivity outside data sensitivity range")
        if not 0 <= self.initial_area_risk < len(self.area_risk_probs):
            raise ValueError("initial_area_risk outside area risk range")
        if self.low_link_offload_penalty < 0.0:
            raise ValueError("low_link_offload_penalty must be non-negative")
        if not 0 <= self.low_link_penalty_threshold < len(self.link_rates_bps):
            raise ValueError("low_link_penalty_threshold outside link range")
        if self.urgency_delay_weight < 0.0:
            raise ValueError("urgency_delay_weight must be non-negative")
        if len(self.task_deadlines) != len(self.task_urgency_probs):
            raise ValueError("task_deadlines length must match task_urgency_probs")
        if any(value <= 0.0 for value in self.task_deadlines):
            raise ValueError("task_deadlines must be positive")
        if self.deadline_miss_penalty < 0.0:
            raise ValueError("deadline_miss_penalty must be non-negative")
        if self.data_sensitivity_offload_penalty < 0.0:
            raise ValueError("data_sensitivity_offload_penalty must be non-negative")
        if self.area_risk_offload_penalty < 0.0:
            raise ValueError("area_risk_offload_penalty must be non-negative")
        if self.cloud_backhaul_delay_per_task < 0.0:
            raise ValueError("cloud_backhaul_delay_per_task must be non-negative")
        if self.cloud_compute_delay_per_task < 0.0:
            raise ValueError("cloud_compute_delay_per_task must be non-negative")
        if self.cloud_delay_scale < 0.0:
            raise ValueError("cloud_delay_scale must be non-negative")
        if self.cloud_usage_penalty_per_task < 0.0:
            raise ValueError("cloud_usage_penalty_per_task must be non-negative")
        if self.low_link_cloud_penalty_per_task < 0.0:
            raise ValueError("low_link_cloud_penalty_per_task must be non-negative")
        if not 0 <= self.low_link_cloud_penalty_threshold < len(self.link_rates_bps):
            raise ValueError("low_link_cloud_penalty_threshold outside link range")
        if self.edge_congestion_penalty_per_task < 0.0:
            raise ValueError("edge_congestion_penalty_per_task must be non-negative")
        if not 0 <= self.edge_congestion_threshold < len(self.edge_load_levels):
            raise ValueError("edge_congestion_threshold outside edge load range")
        if self.cloud_congestion_relief_bonus_per_task < 0.0:
            raise ValueError("cloud_congestion_relief_bonus_per_task must be non-negative")
        if self.cloud_data_sensitivity_multiplier < 1.0:
            raise ValueError("cloud_data_sensitivity_multiplier must be >= 1.0")
        if self.cloud_area_risk_multiplier < 1.0:
            raise ValueError("cloud_area_risk_multiplier must be >= 1.0")
        _validate_probs(self.link_probs, len(self.link_rates_bps), "link_probs")
        _validate_probs(self.edge_load_probs, len(self.edge_load_levels), "edge_load_probs")
        _validate_probs(self.cloud_load_probs, len(self.cloud_load_levels), "cloud_load_probs")
        _validate_probs(self.arrival_probs, len(self.arrival_values), "arrival_probs")
        _validate_probs(self.task_urgency_probs, len(self.task_urgency_probs), "task_urgency_probs")
        _validate_probs(
            self.data_sensitivity_probs,
            len(self.data_sensitivity_probs),
            "data_sensitivity_probs",
        )
        _validate_probs(self.area_risk_probs, len(self.area_risk_probs), "area_risk_probs")


class OffloadingEnv:
    """面向策略训练的离散计算卸载环境。"""

    def __init__(self, config: OffloadingConfig | None = None, seed: int = 0) -> None:
        self.config = config or OffloadingConfig()
        self.config.validate()
        self.rng = np.random.default_rng(seed)
        self.actions = build_action_space(self.config)
        self.codec = build_state_codec(self.config)

    def reset(self, seed: int | None = None) -> OffloadingState:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        return OffloadingState(
            queue=self.config.initial_queue,
            link=self.config.initial_link,
            battery=self.config.initial_battery,
            edge_load=self.config.initial_edge_load,
            task_urgency=self.config.initial_task_urgency,
            data_sensitivity=self.config.initial_data_sensitivity,
            area_risk=self.config.initial_area_risk,
            cloud_load=self.config.initial_cloud_load,
        )

    def encode_state(self, state: OffloadingState) -> int:
        return self.codec.encode(state.as_mapping())

    def decode_state(self, index: int) -> OffloadingState:
        values = self.codec.decode(index)
        return OffloadingState(
            queue=values["queue"],
            link=values["link"],
            battery=values["battery"],
            edge_load=values["edge_load"],
            task_urgency=values["task_urgency"],
            data_sensitivity=values["data_sensitivity"],
            area_risk=values["area_risk"],
            cloud_load=values["cloud_load"],
        )

    def step(self, state: OffloadingState, action: OffloadingAction) -> StepResult:
        breakdown = self.compute_reward(state, action)
        arrival = self._sample_arrival()
        next_state = self._transition(state=state, breakdown=breakdown, arrival=arrival)
        return StepResult(
            state=state,
            action=action,
            reward=breakdown.reward,
            breakdown=breakdown,
            next_state=next_state,
            arrival=arrival,
        )

    def compute_reward(self, state: OffloadingState, action: OffloadingAction) -> RewardBreakdown:
        if action.local_tasks < 0 or action.offload_tasks < 0 or action.cloud_tasks < 0:
            raise ValueError("task counts in action must be non-negative")

        illegal = action.processed_tasks > state.queue or action not in self.actions
        executed = OffloadingAction(0, 0) if illegal else action
        processed = executed.processed_tasks
        rate = self.config.link_rates_bps[state.link]
        edge_load = self.config.edge_load_levels[state.edge_load]
        cloud_load = self.config.cloud_load_levels[state.cloud_load]

        wait_delay = state.queue / max(self.config.avg_arrival_rate, 1e-9)
        local_delay = self.config.cycles_per_task * executed.local_tasks / self.config.local_cpu_hz
        tx_delay = self.config.task_size_bits * executed.offload_tasks / rate
        cloud_tx_delay = self.config.task_size_bits * executed.cloud_tasks / rate
        edge_delay = tx_delay * (1.0 + self.config.edge_delay_scale * edge_load)
        cloud_delay = (
            cloud_tx_delay
            + self.config.cloud_backhaul_delay_per_task * executed.cloud_tasks
            + self.config.cloud_compute_delay_per_task
            * executed.cloud_tasks
            * (1.0 + self.config.cloud_delay_scale * cloud_load)
        )
        delay = wait_delay if processed == 0 else wait_delay + (local_delay + edge_delay + cloud_delay) / processed

        local_energy = (
            self.config.beta
            * (self.config.local_cpu_hz**2)
            * self.config.cycles_per_task
            * executed.local_tasks
        )
        tx_energy = self.config.tx_power_watts * self.config.task_size_bits * executed.remote_tasks / rate
        energy = local_energy + tx_energy

        utility = self.config.theta * np.log1p(processed)
        queue_penalty = self.config.queue_weight * state.queue
        illegal_penalty = self.config.illegal_action_penalty if illegal else 0.0
        low_link_offload_penalty = (
            self.config.low_link_offload_penalty * executed.remote_tasks
            if state.link <= self.config.low_link_penalty_threshold
            else 0.0
        )
        urgency_delay_penalty = self.config.urgency_delay_weight * state.task_urgency * delay
        deadline = self.config.task_deadlines[state.task_urgency]
        deadline_miss_penalty = self.config.deadline_miss_penalty * max(0.0, delay - deadline)
        sensitivity_weighted_remote_tasks = (
            executed.offload_tasks + self.config.cloud_data_sensitivity_multiplier * executed.cloud_tasks
        )
        risk_weighted_remote_tasks = executed.offload_tasks + self.config.cloud_area_risk_multiplier * executed.cloud_tasks
        data_sensitivity_penalty = (
            self.config.data_sensitivity_offload_penalty * state.data_sensitivity * sensitivity_weighted_remote_tasks
        )
        area_risk_penalty = self.config.area_risk_offload_penalty * state.area_risk * risk_weighted_remote_tasks
        cloud_usage_penalty = self.config.cloud_usage_penalty_per_task * executed.cloud_tasks
        low_link_cloud_penalty = (
            self.config.low_link_cloud_penalty_per_task * executed.cloud_tasks
            if state.link <= self.config.low_link_cloud_penalty_threshold
            else 0.0
        )
        edge_congestion_penalty = (
            self.config.edge_congestion_penalty_per_task * executed.offload_tasks
            if state.edge_load >= self.config.edge_congestion_threshold
            else 0.0
        )
        cloud_congestion_relief_bonus = (
            self.config.cloud_congestion_relief_bonus_per_task * executed.cloud_tasks
            if state.edge_load >= self.config.edge_congestion_threshold
            and state.link > self.config.low_link_cloud_penalty_threshold
            else 0.0
        )
        battery_penalty = 4.0 if state.battery <= 0 and processed > 0 else 0.0
        reward = (
            utility
            + cloud_congestion_relief_bonus
            - self.config.delay_weight * delay
            - self.config.energy_weight * energy
            - queue_penalty
            - illegal_penalty
            - low_link_offload_penalty
            - urgency_delay_penalty
            - deadline_miss_penalty
            - data_sensitivity_penalty
            - area_risk_penalty
            - cloud_usage_penalty
            - low_link_cloud_penalty
            - edge_congestion_penalty
            - battery_penalty
        )
        return RewardBreakdown(
            reward=float(reward),
            utility=float(utility),
            delay=float(delay),
            energy=float(energy),
            queue_penalty=float(queue_penalty),
            illegal_penalty=float(illegal_penalty),
            low_link_offload_penalty=float(low_link_offload_penalty),
            urgency_delay_penalty=float(urgency_delay_penalty),
            deadline_miss_penalty=float(deadline_miss_penalty),
            data_sensitivity_penalty=float(data_sensitivity_penalty),
            area_risk_penalty=float(area_risk_penalty),
            cloud_usage_penalty=float(cloud_usage_penalty),
            low_link_cloud_penalty=float(low_link_cloud_penalty),
            edge_congestion_penalty=float(edge_congestion_penalty),
            cloud_congestion_relief_bonus=float(cloud_congestion_relief_bonus),
            executed_action=executed,
        )

    def _transition(self, state: OffloadingState, breakdown: RewardBreakdown, arrival: int) -> OffloadingState:
        processed = breakdown.executed_action.processed_tasks
        next_queue = min(self.config.queue_capacity, max(0, state.queue + arrival - processed))
        battery_drain = int(ceil(breakdown.energy / self.config.battery_energy_per_level_j))
        next_battery = max(0, state.battery - battery_drain)
        return OffloadingState(
            queue=int(next_queue),
            link=self._sample_index(self.config.link_probs),
            battery=int(next_battery),
            edge_load=self._sample_index(self.config.edge_load_probs),
            task_urgency=self._sample_index(self.config.task_urgency_probs),
            data_sensitivity=self._sample_index(self.config.data_sensitivity_probs),
            area_risk=self._sample_index(self.config.area_risk_probs),
            cloud_load=self._sample_index(self.config.cloud_load_probs),
        )

    def _sample_arrival(self) -> int:
        index = self._sample_index(self.config.arrival_probs)
        return int(self.config.arrival_values[index])

    def _sample_index(self, probs: tuple[float, ...]) -> int:
        return int(self.rng.choice(np.arange(len(probs)), p=np.asarray(probs, dtype=np.float64)))


def build_action_space(config: OffloadingConfig) -> tuple[OffloadingAction, ...]:
    return tuple(
        OffloadingAction(local, offload, cloud)
        for local, offload, cloud in product(
            range(config.max_local_tasks + 1),
            range(config.max_offload_tasks + 1),
            range(config.max_cloud_tasks + 1),
        )
    )


def build_state_codec(config: OffloadingConfig) -> StateCodec:
    return StateCodec(
        (
            ("queue", config.queue_capacity + 1),
            ("link", len(config.link_rates_bps)),
            ("battery", config.battery_level_count),
            ("edge_load", len(config.edge_load_levels)),
            ("task_urgency", len(config.task_urgency_probs)),
            ("data_sensitivity", len(config.data_sensitivity_probs)),
            ("area_risk", len(config.area_risk_probs)),
            ("cloud_load", len(config.cloud_load_levels)),
        )
    )


def _validate_probs(values: tuple[float, ...], expected_len: int, name: str) -> None:
    if len(values) != expected_len:
        raise ValueError(f"{name} length must be {expected_len}")
    if any(value < 0.0 for value in values):
        raise ValueError(f"{name} must be non-negative")
    total = sum(values)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"{name} must sum to 1.0, got {total}")
