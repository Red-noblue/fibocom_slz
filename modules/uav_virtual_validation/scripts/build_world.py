from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.artifacts.io import write_json
from uav_virtual_validation.exporters.czml import world_route_to_czml
from uav_virtual_validation.exporters.geojson import world_to_geojson
from uav_virtual_validation.scenarios.loader import load_json, load_scenario
from uav_virtual_validation.world.generator import generate_world


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成第一阶段 UAV 3D 城市仿真世界资产。")
    parser.add_argument("--scenario", default=str(ROOT / "configs/scenarios/strong_headwind_route.json"))
    parser.add_argument("--world", default=str(ROOT / "configs/worlds/urban_grid_world.json"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/urban_grid_world"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario = load_scenario(args.scenario)
    world_cfg = load_json(args.world)
    world = generate_world(scenario, world_cfg)

    out = Path(args.output_dir)
    write_json(
        {
            "name": world.name,
            "origin": {"lat": world.origin_lat, "lon": world.origin_lon},
            "route_length_m": world.route_length_m,
            "route_heading_deg": world.route_heading_deg,
            "building_count": len(world.buildings),
            "no_fly_zone_count": len(world.no_fly_zones),
            "weather_sample_count": len(world.weather_samples),
        },
        out / "world_summary.json",
    )
    write_json(world_to_geojson(world), out / "world.geojson")
    write_json(world_route_to_czml(world, float(scenario["cruise_altitude_m"])), out / "route.czml")
    print(f"world summary: {out / 'world_summary.json'}")
    print(f"world geojson: {out / 'world.geojson'}")
    print(f"route czml: {out / 'route.czml'}")


if __name__ == "__main__":
    main()
