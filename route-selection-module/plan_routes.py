"""命令行入口：读取武汉城市资产并输出多条候选航线结果。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from route_selection import CityRoutePlanner, PlannerRequest
from route_selection.io import read_json, resolve_city_assets, route_result_to_geojson, write_json


DEFAULT_CITY_DIR = Path("/home/fibo/fibocom_slz/modules/uav_virtual_validation/outputs/real_city/wuhan_central_urban")
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "latest"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="依据城市天气场与建筑分布生成多条无人机候选航线。")
    parser.add_argument("--city-dir", default=str(DEFAULT_CITY_DIR), help="城市资产目录。")
    parser.add_argument("--weather-path", default=None, help="天气场 GeoJSON，默认使用 city-dir/real_weather_field.geojson。")
    parser.add_argument("--buildings-path", default=None, help="建筑 GeoJSON，默认使用 city-dir/real_buildings.geojson。")
    parser.add_argument("--city-config-path", default=None, help="城市快照 JSON，默认使用 city-dir/city_config_snapshot.json。")
    parser.add_argument("--city-summary-path", default=None, help="城市摘要 JSON，默认使用 city-dir/city_summary.json。")
    parser.add_argument("--start-lat", type=float, required=True, help="起点纬度。")
    parser.add_argument("--start-lon", type=float, required=True, help="起点经度。")
    parser.add_argument("--end-lat", type=float, required=True, help="终点纬度。")
    parser.add_argument("--end-lon", type=float, required=True, help="终点经度。")
    parser.add_argument(
        "--planning-mode",
        default=CityRoutePlanner.PLANNING_MODE_COMBINED,
        choices=sorted(CityRoutePlanner.PLANNING_MODES),
        help="路径规划模式：仅天气、仅建筑、或综合。",
    )
    parser.add_argument("--start-altitude-m", type=float, default=120.0, help="起点规划高度。")
    parser.add_argument("--end-altitude-m", type=float, default=120.0, help="终点规划高度。")
    parser.add_argument("--min-altitude-m", type=float, default=0.0, help="最低规划高度，默认不限制。")
    parser.add_argument("--candidate-count", type=int, default=5, help="候选航线数量，当前最多 5 条。")
    parser.add_argument("--cell-m", type=float, default=220.0, help="规划栅格边长，单位米。")
    parser.add_argument("--safety-clearance-m", type=float, default=25.0, help="楼顶安全净空。")
    parser.add_argument("--cruise-speed-mps", type=float, default=14.0, help="巡航速度。")
    parser.add_argument("--climb-speed-mps", type=float, default=4.0, help="爬升速度。")
    parser.add_argument("--descend-speed-mps", type=float, default=5.0, help="下降速度。")
    parser.add_argument("--max-altitude-m", type=float, default=None, help="最大规划高度，默认自动推断。")
    parser.add_argument("--output-dir", default=None, help="输出目录，默认写入 outputs/latest/<planning_mode>。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asset_paths = resolve_city_assets(
        city_dir=args.city_dir,
        weather_path=args.weather_path,
        buildings_path=args.buildings_path,
        city_config_path=args.city_config_path,
        city_summary_path=args.city_summary_path,
    )
    planner = CityRoutePlanner.from_payloads(
        city_config=read_json(asset_paths["city_config"]),
        city_summary=read_json(asset_paths["city_summary"]),
        buildings_geojson=read_json(asset_paths["buildings"]),
        weather_geojson=read_json(asset_paths["weather"]),
        ground_geojson=read_json(asset_paths["ground"]) if asset_paths["ground"].exists() else None,
    )
    result = planner.plan(
        PlannerRequest(
            start_lat=args.start_lat,
            start_lon=args.start_lon,
            end_lat=args.end_lat,
            end_lon=args.end_lon,
            planning_mode=args.planning_mode,
            start_altitude_m=args.start_altitude_m,
            end_altitude_m=args.end_altitude_m,
            min_altitude_m=args.min_altitude_m,
            candidate_count=args.candidate_count,
            cell_m=args.cell_m,
            safety_clearance_m=args.safety_clearance_m,
            cruise_speed_mps=args.cruise_speed_mps,
            climb_speed_mps=args.climb_speed_mps,
            descend_speed_mps=args.descend_speed_mps,
            max_altitude_m=args.max_altitude_m,
        )
    )
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_ROOT / args.planning_mode
    result_json = result.to_dict()
    result_geojson = route_result_to_geojson(result_json)
    write_json(result_json, output_dir / "route_candidates.json")
    write_json(result_geojson, output_dir / "route_candidates.geojson")
    for route in result_json["routes"]:
        write_json(
            {
                "type": "FeatureCollection",
                "name": route["route_id"],
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "route_id": route["route_id"],
                            "label": route["label"],
                            "strategy": route["strategy"],
                            "score": route["score"],
                            "topsis_score": route.get("topsis_score"),
                            "robustness_score": route.get("robustness_score"),
                            "reliability_ratio": route.get("reliability_ratio"),
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[point["lon"], point["lat"], point["altitude_m"]] for point in route["waypoints"]],
                        },
                    }
                ],
            },
            output_dir / f"{route['route_id']}.geojson",
        )
    print(f"route_candidates_json={output_dir / 'route_candidates.json'}")
    print(f"route_candidates_geojson={output_dir / 'route_candidates.geojson'}")
    print(f"route_count={len(result_json['routes'])}")
    for route in result_json["routes"]:
        print(
            f"{route['route_id']} label={route['label']} score={route['score']} "
            f"robustness={route.get('robustness_score')} "
            f"distance_m={route['distance_m']} duration_s={route['estimated_duration_s']}"
        )


if __name__ == "__main__":
    main()
