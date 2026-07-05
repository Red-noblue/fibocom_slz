from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.artifacts.io import write_sim_outputs
from uav_virtual_validation.scenarios.loader import load_scenario
from uav_virtual_validation.simulators.simple import simulate_scenario


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行第一阶段简化 UAV 虚拟仿真。")
    parser.add_argument("--scenario", default=str(ROOT / "configs/scenarios/strong_headwind_route.json"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/strong_headwind_route"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    scenario = load_scenario(args.scenario)
    result = simulate_scenario(scenario)
    paths = write_sim_outputs(result, args.output_dir)
    print(f"sim summary: {paths['summary']}")
    print(f"sim timeseries: {paths['timeseries']}")
