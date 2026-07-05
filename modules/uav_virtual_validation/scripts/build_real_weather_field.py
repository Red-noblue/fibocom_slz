from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.artifacts.io import read_json, write_json
from uav_virtual_validation.weather.field import build_real_weather_field_geojson


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 Open-Meteo 历史天气生成真实城市三维天气场。")
    parser.add_argument("--city", default=str(ROOT / "outputs/real_city/manhattan_midtown/city_config_snapshot.json"))
    parser.add_argument("--weather", default=str(ROOT / "outputs/real_city/manhattan_midtown/historical_weather_open_meteo.json"))
    parser.add_argument("--output", default=str(ROOT / "outputs/real_city/manhattan_midtown/real_weather_field.geojson"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    city = read_json(args.city)
    weather = read_json(args.weather)
    field = build_real_weather_field_geojson(city, weather)
    write_json(field, args.output)
    print(f"weather field: {args.output} ({len(field['features'])} features)")
