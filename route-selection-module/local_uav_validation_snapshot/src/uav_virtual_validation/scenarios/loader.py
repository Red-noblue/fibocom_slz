"""加载并解析 UAV 虚拟验证场景配置。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_config_path(base_file: str | Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (Path(base_file).parent / path).resolve()


def load_scenario(path: str | Path) -> dict[str, Any]:
    scenario_path = Path(path).resolve()
    scenario = load_json(scenario_path)
    scenario["_scenario_path"] = str(scenario_path)
    scenario["vehicle"] = load_json(resolve_config_path(scenario_path, scenario["vehicle_config"]))
    scenario["environment"] = load_json(resolve_config_path(scenario_path, scenario["environment_config"]))
    scenario["weather"] = load_json(resolve_config_path(scenario_path, scenario["weather_config"]))
    return scenario
