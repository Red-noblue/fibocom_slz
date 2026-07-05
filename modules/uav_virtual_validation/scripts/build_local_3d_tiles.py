from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.tiles.gltf_tiles import build_city_tileset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把真实城市 OSM 建筑转换为本地 3D Tiles。")
    parser.add_argument("--city-dir", default=str(ROOT / "outputs/real_city/manhattan_midtown"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    city_dir = Path(args.city_dir)
    paths = build_city_tileset(
        city_dir / "real_buildings.geojson",
        city_dir / "city_summary.json",
        city_dir / "tiles",
    )
    print(f"tileset: {paths['tileset']}")
    print(f"gltf: {paths['gltf']}")
    print(f"ground tileset: {paths['ground_tileset']}")
    print(f"ground gltf: {paths['ground_gltf']}")
    print(f"outline tileset: {paths['outline_tileset']}")
    print(f"outline gltf: {paths['outline_gltf']}")
