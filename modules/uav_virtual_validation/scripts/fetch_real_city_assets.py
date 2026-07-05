from __future__ import annotations

import argparse
import sys
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.artifacts.io import write_json
from uav_virtual_validation.real_city.osm import (
    build_overpass_query,
    city_ground_geojson,
    city_route_geojson,
    city_route_length_m,
    fetch_overpass,
    load_city_config,
    overpass_to_building_geojson,
)
from uav_virtual_validation.weather.open_meteo import fetch_historical_weather, write_weather_artifacts
from uav_virtual_validation.weather.field import build_real_weather_field_geojson


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取真实城市建筑和历史天气资产。")
    parser.add_argument("--city", default=str(ROOT / "configs/cities/manhattan_midtown.json"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/real_city/manhattan_midtown"))
    parser.add_argument("--overpass-url", default=None, help="可选的 Overpass API 端点，用于公共服务限流时切换备用源。")
    parser.add_argument("--skip-osm", action="store_true")
    parser.add_argument("--skip-weather", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    city = load_city_config(args.city)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    write_json(city, out / "city_config_snapshot.json")
    write_json(city_route_geojson(city), out / "route.geojson")
    summary = {
        "name": city["name"],
        "display_name": city.get("display_name", city["name"]),
        "description": city.get("description", ""),
        "center": city["center"],
        "bbox": city["bbox"],
        "route_length_m": city_route_length_m(city),
        "route_waypoint_count": len(city["default_route"]),
        "building_count": 0,
        "weather_sample_count": 0,
        "data_sources": ["OpenStreetMap", "Open-Meteo"],
    }

    if not args.skip_osm:
        query = build_overpass_query(city)
        (out / "overpass_query.txt").write_text(query, encoding="utf-8")
        payload = fetch_overpass(query, url=args.overpass_url) if args.overpass_url else fetch_overpass(query)
        buildings = overpass_to_building_geojson(city, payload)
        ground = city_ground_geojson(city, payload)
        write_json(buildings, out / "real_buildings.geojson")
        write_json(ground, out / "ground_layers.geojson")
        summary["building_count"] = len(buildings["features"])
        summary["ground_feature_count"] = len(ground["features"])
        print(f"real buildings: {out / 'real_buildings.geojson'} ({len(buildings['features'])} features)")
        print(f"ground layers: {out / 'ground_layers.geojson'} ({len(ground['features'])} features)")
    elif (out / "real_buildings.geojson").exists():
        with (out / "real_buildings.geojson").open("r", encoding="utf-8") as fh:
            summary["building_count"] = len(json.load(fh).get("features", []))
        if (out / "ground_layers.geojson").exists():
            with (out / "ground_layers.geojson").open("r", encoding="utf-8") as fh:
                summary["ground_feature_count"] = len(json.load(fh).get("features", []))

    if not args.skip_weather:
        weather = fetch_historical_weather(city)
        paths = write_weather_artifacts(weather, out)
        field = build_real_weather_field_geojson(city, weather)
        write_json(field, out / "real_weather_field.geojson")
        summary["weather_sample_count"] = len(field["features"])
        summary["weather_hour_count"] = len(weather.get("hourly", {}).get("time", []))
        print(f"historical weather: {paths['raw']}")
        print(f"weather field: {out / 'real_weather_field.geojson'} ({len(field['features'])} features)")
    elif (out / "historical_weather_open_meteo.json").exists():
        with (out / "historical_weather_open_meteo.json").open("r", encoding="utf-8") as fh:
            weather = json.load(fh)
            summary["weather_hour_count"] = len(weather.get("hourly", {}).get("time", []))
        if (out / "real_weather_field.geojson").exists():
            with (out / "real_weather_field.geojson").open("r", encoding="utf-8") as fh:
                summary["weather_sample_count"] = len(json.load(fh).get("features", []))

    write_json(summary, out / "city_summary.json")
    print(f"route: {out / 'route.geojson'}")
    print(f"city summary: {out / 'city_summary.json'}")
    print(f"city snapshot: {out / 'city_config_snapshot.json'}")


if __name__ == "__main__":
    main()
