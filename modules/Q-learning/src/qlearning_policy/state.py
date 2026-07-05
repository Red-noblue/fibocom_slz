# 中文说明：本文件提供离散状态和整数索引之间的编码器，便于维护 Q 表。
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class StateCodec:
    """把多个离散状态字段编码为一个 Q 表索引。"""

    fields: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if not self.fields:
            raise ValueError("fields must not be empty")

        multipliers: list[int] = []
        scale = 1
        for name, size in reversed(self.fields):
            if size <= 0:
                raise ValueError(f"state field {name} size must be positive")
            multipliers.append(scale)
            scale *= size

        object.__setattr__(self, "_multipliers", tuple(reversed(multipliers)))
        object.__setattr__(self, "size", scale)

    def encode(self, state: Mapping[str, int]) -> int:
        index = 0
        for (name, size), multiplier in zip(self.fields, self._multipliers, strict=True):
            value = int(state[name])
            if value < 0 or value >= size:
                raise ValueError(f"state field {name}={value} outside [0, {size})")
            index += value * multiplier
        return int(index)

    def decode(self, index: int) -> dict[str, int]:
        if index < 0 or index >= self.size:
            raise ValueError(f"state index {index} outside [0, {self.size})")

        remaining = int(index)
        state: dict[str, int] = {}
        for (name, size), multiplier in zip(self.fields, self._multipliers, strict=True):
            value = remaining // multiplier
            if value >= size:
                raise ValueError(f"decoded field {name}={value} outside [0, {size})")
            state[name] = int(value)
            remaining -= int(value) * multiplier
        return state

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(name for name, _size in self.fields)
