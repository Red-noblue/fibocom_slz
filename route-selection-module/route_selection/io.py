"""输入输出工具：读取现有城市资产，并把候选航线导出为 JSON/GeoJSON。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WEATHER_OVERRIDE_ROOT = Path(__file__).resolve().parent.parent / "weather_overrides"


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def write_json(data: dict[str, Any], path: str | Path) -> None:
    output_path = Path(path)
    ensure_dir(output_path.parent)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, ensure_ascii=False, indent=2)


def resolve_city_assets(
    city_dir: str | Path,
    weather_path: str | Path | None = None,
    buildings_path: str | Path | None = None,
    city_config_path: str | Path | None = None,
    city_summary_path: str | Path | None = None,
) -> dict[str, Path]:
    city_dir_path = Path(city_dir)
    weather_override_path = WEATHER_OVERRIDE_ROOT / city_dir_path.name / "real_weather_field.geojson"
    return {
        "city_dir": city_dir_path,
        "city_config": Path(city_config_path) if city_config_path else city_dir_path / "city_config_snapshot.json",
        "city_summary": Path(city_summary_path) if city_summary_path else city_dir_path / "city_summary.json",
        "weather": Path(weather_path)
        if weather_path
        else (weather_override_path if weather_override_path.exists() else city_dir_path / "real_weather_field.geojson"),
        "buildings": Path(buildings_path) if buildings_path else city_dir_path / "real_buildings.geojson",
        "ground": city_dir_path / "ground_layers.geojson",
    }


def route_result_to_geojson(result: dict[str, Any]) -> dict[str, Any]:
    planning_mode = (result.get("planner") or {}).get("planning_mode")
    features: list[dict[str, Any]] = []
    for route in result.get("routes", []):
        coordinates = [[point["lon"], point["lat"], point["altitude_m"]] for point in route["waypoints"]]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "route_id": route["route_id"],
                    "label": route["label"],
                    "strategy": route["strategy"],
                    "planning_mode": planning_mode,
                    "score": route["score"],
                    "base_cost": route.get("base_cost"),
                    "topsis_score": route.get("topsis_score"),
                    "robustness_score": route.get("robustness_score"),
                    "reliability_ratio": route.get("reliability_ratio"),
                    "duration_p95_s": route.get("duration_p95_s"),
                    "expected_delay_ratio": route.get("expected_delay_ratio"),
                    "distance_m": route["distance_m"],
                    "estimated_duration_s": route["estimated_duration_s"],
                    "max_wind_speed_mps": route["max_wind_speed_mps"],
                    "max_headwind_mps": route["max_headwind_mps"],
                    "max_crosswind_mps": route["max_crosswind_mps"],
                    "max_turbulence_index": route["max_turbulence_index"],
                    "max_precipitation_mm": route.get("max_precipitation_mm"),
                    "max_weather_risk_score": route.get("max_weather_risk_score"),
                    "high_risk_exposure_ratio": route.get("high_risk_exposure_ratio"),
                    "average_urban_density": route["average_urban_density"],
                    "average_connectivity_index": route.get("average_connectivity_index"),
                    "minimum_connectivity_index": route.get("minimum_connectivity_index"),
                    "average_reachability_index": route.get("average_reachability_index"),
                    "corridor_diversity_index": route.get("corridor_diversity_index"),
                    "overflight_building_count": route.get("overflight_building_count"),
                    "overflight_exposure_index": route.get("overflight_exposure_index"),
                    "waypoint_count": route["waypoint_count"],
                    "recommended_rank": route["recommended_rank"],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "name": f"{result['city']['name']}_route_candidates",
        "planning_mode": planning_mode,
        "features": features,
    }
