# 中文说明：本文件定义覆盖场景配置，把网络覆盖抽象为链路状态和边缘负载概率。
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .offloading import OffloadingConfig


CoverageScenarioName = Literal[
    "balanced",
    "good_coverage",
    "weak_coverage",
    "intermittent_coverage",
    "congested_edge",
]


@dataclass(frozen=True)
class CoverageScenario:
    name: str
    description: str
    link_probs: tuple[float, ...]
    edge_load_probs: tuple[float, ...]
    cloud_load_probs: tuple[float, ...]


COVERAGE_SCENARIOS: dict[str, CoverageScenario] = {
    "balanced": CoverageScenario(
        name="balanced",
        description="默认混合覆盖场景，链路和边缘负载均处于中等波动。",
        link_probs=(0.25, 0.50, 0.25),
        edge_load_probs=(0.30, 0.50, 0.20),
        cloud_load_probs=(0.35, 0.45, 0.20),
    ),
    "good_coverage": CoverageScenario(
        name="good_coverage",
        description="良好覆盖场景，高速链路更常见，边缘节点较少拥塞。",
        link_probs=(0.05, 0.25, 0.70),
        edge_load_probs=(0.45, 0.40, 0.15),
        cloud_load_probs=(0.45, 0.40, 0.15),
    ),
    "weak_coverage": CoverageScenario(
        name="weak_coverage",
        description="弱覆盖场景，低速链路更常见，适合观察策略是否减少卸载。",
        link_probs=(0.70, 0.25, 0.05),
        edge_load_probs=(0.30, 0.50, 0.20),
        cloud_load_probs=(0.35, 0.45, 0.20),
    ),
    "intermittent_coverage": CoverageScenario(
        name="intermittent_coverage",
        description="间歇覆盖场景，低速和高速链路频繁切换，中等链路较少。",
        link_probs=(0.45, 0.10, 0.45),
        edge_load_probs=(0.25, 0.45, 0.30),
        cloud_load_probs=(0.30, 0.45, 0.25),
    ),
    "congested_edge": CoverageScenario(
        name="congested_edge",
        description="边缘拥塞场景，链路不一定差，但边缘节点高负载更常见。",
        link_probs=(0.20, 0.45, 0.35),
        edge_load_probs=(0.10, 0.30, 0.60),
        cloud_load_probs=(0.55, 0.35, 0.10),
    ),
}


def make_offloading_config_for_coverage(
    scenario_name: CoverageScenarioName | str,
    base_config: OffloadingConfig | None = None,
) -> OffloadingConfig:
    scenario = get_coverage_scenario(scenario_name)
    config = replace(
        base_config or OffloadingConfig(),
        link_probs=scenario.link_probs,
        edge_load_probs=scenario.edge_load_probs,
        cloud_load_probs=scenario.cloud_load_probs,
    )
    config.validate()
    return config


def make_conservative_offloading_config_for_coverage(
    scenario_name: CoverageScenarioName | str,
    base_config: OffloadingConfig | None = None,
    *,
    low_link_offload_penalty: float = 16.0,
    low_link_penalty_threshold: int = 0,
) -> OffloadingConfig:
    config = replace(
        make_offloading_config_for_coverage(scenario_name, base_config=base_config),
        low_link_offload_penalty=low_link_offload_penalty,
        low_link_penalty_threshold=low_link_penalty_threshold,
    )
    config.validate()
    return config


def get_coverage_scenario(scenario_name: CoverageScenarioName | str) -> CoverageScenario:
    try:
        return COVERAGE_SCENARIOS[scenario_name]
    except KeyError as exc:
        choices = ", ".join(sorted(COVERAGE_SCENARIOS))
        raise ValueError(f"unknown coverage scenario {scenario_name!r}, choices: {choices}") from exc


def list_coverage_scenario_names() -> tuple[str, ...]:
    return tuple(COVERAGE_SCENARIOS)
