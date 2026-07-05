# 中文说明：本文件实现表格型 Q-learning 智能体，作为后续 DQN/PPO 前的可解释基线。
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class QLearningParams:
    """Q-learning 训练超参数。"""

    alpha: float = 0.1
    gamma: float = 0.95
    epsilon: float = 0.1

    def validate(self) -> None:
        if not 0.0 < self.alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        if not 0.0 <= self.gamma <= 1.0:
            raise ValueError("gamma must be in [0, 1]")
        if not 0.0 <= self.epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")


class QLearningAgent:
    """最小表格型 Q-learning 智能体。"""

    def __init__(
        self,
        state_count: int,
        action_count: int,
        params: QLearningParams | None = None,
        seed: int = 0,
    ) -> None:
        if state_count <= 0 or action_count <= 0:
            raise ValueError("state_count and action_count must be positive")
        self.params = params or QLearningParams()
        self.params.validate()
        self.state_count = state_count
        self.action_count = action_count
        self.q_table = np.zeros((state_count, action_count), dtype=np.float64)
        self.rng = np.random.default_rng(seed)

    def select_action(self, state_index: int, *, explore: bool = True) -> int:
        self._validate_state_index(state_index)
        if explore and self.rng.random() < self.params.epsilon:
            return int(self.rng.integers(self.action_count))
        return self.greedy_action(state_index)

    def greedy_action(self, state_index: int) -> int:
        self._validate_state_index(state_index)
        state_values = self.q_table[state_index]
        best_value = np.max(state_values)
        candidates = np.flatnonzero(np.isclose(state_values, best_value))
        return int(self.rng.choice(candidates))

    def update(self, state_index: int, action_index: int, reward: float, next_state_index: int) -> None:
        self._validate_state_index(state_index)
        self._validate_state_index(next_state_index)
        if action_index < 0 or action_index >= self.action_count:
            raise ValueError(f"action_index {action_index} outside [0, {self.action_count})")

        old_value = self.q_table[state_index, action_index]
        next_best = np.max(self.q_table[next_state_index])
        target = reward + self.params.gamma * next_best
        self.q_table[state_index, action_index] = old_value + self.params.alpha * (target - old_value)

    def _validate_state_index(self, state_index: int) -> None:
        if state_index < 0 or state_index >= self.state_count:
            raise ValueError(f"state_index {state_index} outside [0, {self.state_count})")
