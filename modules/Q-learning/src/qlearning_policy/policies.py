# 中文说明：本文件提供可解释基线策略，用于和 Q-learning 策略做对比。
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .offloading import OffloadingAction, OffloadingEnv, OffloadingState


class Policy(Protocol):
    def select_action(self, state: OffloadingState, env: OffloadingEnv) -> OffloadingAction:
        """根据当前状态选择动作。"""


@dataclass(frozen=True)
class LocalOnlyPolicy:
    """全部优先本地计算。"""

    def select_action(self, state: OffloadingState, env: OffloadingEnv) -> OffloadingAction:
        return OffloadingAction(local_tasks=min(env.config.max_local_tasks, state.queue), offload_tasks=0)


@dataclass(frozen=True)
class OffloadOnlyPolicy:
    """全部优先边缘卸载。"""

    def select_action(self, state: OffloadingState, env: OffloadingEnv) -> OffloadingAction:
        return OffloadingAction(local_tasks=0, offload_tasks=min(env.config.max_offload_tasks, state.queue))


@dataclass(frozen=True)
class CloudOnlyPolicy:
    """全部优先云端卸载。"""

    def select_action(self, state: OffloadingState, env: OffloadingEnv) -> OffloadingAction:
        return OffloadingAction(
            local_tasks=0,
            offload_tasks=0,
            cloud_tasks=min(env.config.max_cloud_tasks, state.queue),
        )


@dataclass(frozen=True)
class RuleBasedOffloadingPolicy:
    """面向端边云卸载的简单规则基线。"""

    def select_action(self, state: OffloadingState, env: OffloadingEnv) -> OffloadingAction:
        if state.queue <= 0:
            return OffloadingAction(0, 0)

        high_link = state.link >= len(env.config.link_rates_bps) - 1
        low_edge_load = state.edge_load == 0
        high_edge_load = state.edge_load >= len(env.config.edge_load_levels) - 1
        low_cloud_load = state.cloud_load == 0
        enough_battery = state.battery >= 2
        remote_sensitive = state.data_sensitivity >= 2 or state.area_risk >= 2

        if remote_sensitive and enough_battery:
            return OffloadingAction(local_tasks=min(env.config.max_local_tasks, state.queue), offload_tasks=0)
        if high_link and high_edge_load and low_cloud_load and not remote_sensitive:
            return OffloadingAction(
                local_tasks=0,
                offload_tasks=0,
                cloud_tasks=min(env.config.max_cloud_tasks, state.queue),
            )
        if high_link and low_edge_load and state.queue >= 3 and enough_battery:
            cloud_tasks = min(env.config.max_cloud_tasks, max(0, state.queue - 2))
            return OffloadingAction(local_tasks=1, offload_tasks=1, cloud_tasks=cloud_tasks)
        if high_link and state.edge_load <= 1:
            return OffloadingAction(local_tasks=0, offload_tasks=min(env.config.max_offload_tasks, state.queue))
        if enough_battery:
            return OffloadingAction(local_tasks=min(env.config.max_local_tasks, state.queue), offload_tasks=0)
        return OffloadingAction(0, 0)
