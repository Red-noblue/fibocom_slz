"""把天启目录下的武汉垂直气象模型转换为武汉城市场景可直接使用的天气覆盖层。"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TIANQI_ROOT = Path("/home/fibo/tianqi")
if str(TIANQI_ROOT) not in sys.path:
    sys.path.insert(0, str(TIANQI_ROOT))

from build_qingyuan_vertical_model import dewpoint_from_vapor_pressure_hpa, saturation_vapor_pressure_hpa
from show_qingyuan_height_weather import load_hybrid_model

from route_selection.io import WEATHER_OVERRIDE_ROOT, read_json, write_json

REAL_CITY_ROOT = Path("/home/fibo/fibocom_slz/modules/uav_virtual_validation/outputs/real_city")
DEFAULT_MODEL_PATH = TIANQI_ROOT / "outputs_wuhan_vertical_lowalt" / "wuhan_vertical_model.pkl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入武汉垂直气象模型并生成武汉场景天气覆盖层。")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="武汉低空气象垂直模型路径。",
    )
    parser.add_argument(
        "--city-root",
        type=Path,
        default=REAL_CITY_ROOT,
        help="真实城市资产根目录。",
    )
    parser.add_argument(
        "--city",
        action="append",
        default=[],
        help="指定一个或多个武汉场景目录名；不传时自动处理所有 wuhan_* 场景。",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=WEATHER_OVERRIDE_ROOT,
        help="天气覆盖层输出目录。",
    )
    return parser.parse_args()


def list_wuhan_cities(city_root: Path, explicit_cities: list[str]) -> list[str]:
    if explicit_cities:
        return explicit_cities
    return sorted(path.name for path in city_root.iterdir() if path.is_dir() and path.name.startswith("wuhan_"))


def altitude_from_feature(feature: dict[str, Any]) -> float:
    coordinates = feature.get("geometry", {}).get("coordinates", [])
    props = feature.get("properties", {})
    if len(coordinates) >= 3:
        return float(coordinates[2])
    return float(props.get("altitude_m") or 0.0)


def dewpoint_from_temp_rh(temp_c: float, relative_humidity_pct: float) -> float:
    rh_ratio = min(1.0, max(0.01, relative_humidity_pct / 100.0))
    vapor_pressure_hpa = float(saturation_vapor_pressure_hpa(temp_c)) * rh_ratio
    return float(dewpoint_from_vapor_pressure_hpa(vapor_pressure_hpa))


def angle_gap_deg(a_deg: float, b_deg: float) -> float:
    return abs(((a_deg - b_deg + 180.0) % 360.0) - 180.0)


def derive_turbulence_index(
    *,
    anchor_turbulence: float,
    original_turbulence: float,
    anchor_speed_mps: float,
    target_speed_mps: float,
    anchor_dir_deg: float,
    target_dir_deg: float,
    surface_altitude_m: float,
    target_altitude_m: float,
) -> float:
    shear_speed = abs(target_speed_mps - anchor_speed_mps)
    turn_ratio = angle_gap_deg(target_dir_deg, anchor_dir_deg) / 180.0
    height_ratio = max(0.0, target_altitude_m - surface_altitude_m) / 220.0
    turbulence = (
        original_turbulence * 0.55
        + anchor_turbulence * 0.20
        + shear_speed * 0.045
        + turn_ratio * 0.16
        + height_ratio * 0.05
    )
    return round(max(0.02, min(1.0, turbulence)), 3)


def convert_city_weather(city_name: str, city_root: Path, output_root: Path, model_path: Path) -> dict[str, Any]:
    source_path = city_root / city_name / "real_weather_field.geojson"
    source_geojson = read_json(source_path)
    features = source_geojson.get("features", [])
    grouped: dict[tuple[float, float], list[dict[str, Any]]] = {}
    for feature in features:
        geom = feature.get("geometry", {})
        if geom.get("type") != "Point":
            continue
        lon, lat = geom.get("coordinates", [0.0, 0.0])[:2]
        grouped.setdefault((round(float(lon), 7), round(float(lat), 7)), []).append(feature)

    model = load_hybrid_model(model_path)
    converted_features: list[dict[str, Any]] = []
    for point_features in grouped.values():
        point_features.sort(key=altitude_from_feature)
        anchor_feature = point_features[0]
        anchor_props = dict(anchor_feature.get("properties", {}))
        surface_altitude_m = altitude_from_feature(anchor_feature)
        surface_temp_c = float(anchor_props.get("temperature_c") or 0.0)
        surface_pressure_hpa = float(anchor_props.get("pressure_hpa") or 1013.25)
        surface_rh_pct = float(anchor_props.get("relative_humidity_pct") or 75.0)
        surface_dewpoint_c = dewpoint_from_temp_rh(surface_temp_c, surface_rh_pct)
        surface_wind_dir_deg = float(anchor_props.get("wind_dir_deg") or 0.0)
        surface_wind_speed_mps = float(anchor_props.get("wind_speed_mps") or 0.0)
        anchor_turbulence = float(anchor_props.get("turbulence_index") or 0.12)

        for feature in point_features:
            geom = feature.get("geometry", {})
            coords = list(geom.get("coordinates", []))
            lon = float(coords[0])
            lat = float(coords[1])
            target_altitude_m = altitude_from_feature(feature)
            props = dict(feature.get("properties", {}))
            original_turbulence = float(props.get("turbulence_index") or anchor_turbulence)
            if math.isclose(target_altitude_m, surface_altitude_m, abs_tol=1e-6):
                pred_temp_c = surface_temp_c
                pred_pressure_hpa = surface_pressure_hpa
                pred_dewpoint_c = surface_dewpoint_c
                pred_rh_pct = surface_rh_pct
                pred_wind_dir_deg = surface_wind_dir_deg
                pred_wind_speed_mps = surface_wind_speed_mps
            else:
                prediction = model.predict_from_surface(
                    surface_pressure_hpa=surface_pressure_hpa,
                    surface_temp_c=surface_temp_c,
                    surface_dewpoint_c=surface_dewpoint_c,
                    surface_wind_dir_deg=surface_wind_dir_deg,
                    surface_wind_speed_mps=surface_wind_speed_mps,
                    surface_height_m=surface_altitude_m,
                    target_height_m=target_altitude_m,
                ).iloc[0]
                pred_temp_c = float(prediction["pred_temp_c"])
                pred_pressure_hpa = float(prediction["pred_pressure_hpa"])
                pred_dewpoint_c = float(prediction["pred_dewpoint_c"])
                pred_rh_pct = float(prediction["pred_rh_pct"])
                pred_wind_dir_deg = float(prediction["pred_wind_dir_deg"])
                pred_wind_speed_mps = float(prediction["pred_wind_speed_mps"])
            converted_props = dict(props)
            converted_props.update(
                {
                    "source": "tianqi_wuhan_vertical_model",
                    "source_detail": "open_meteo_surface_anchor+vertical_profile_fit",
                    "altitude_m": round(target_altitude_m, 1),
                    "wind_speed_mps": round(pred_wind_speed_mps, 2),
                    "wind_dir_deg": round(pred_wind_dir_deg, 1),
                    "temperature_c": round(pred_temp_c, 2),
                    "pressure_hpa": round(pred_pressure_hpa, 2),
                    "relative_humidity_pct": round(max(0.0, min(100.0, pred_rh_pct)), 1),
                    "dewpoint_c": round(pred_dewpoint_c, 2),
                    "turbulence_index": derive_turbulence_index(
                        anchor_turbulence=anchor_turbulence,
                        original_turbulence=original_turbulence,
                        anchor_speed_mps=surface_wind_speed_mps,
                        target_speed_mps=pred_wind_speed_mps,
                        anchor_dir_deg=surface_wind_dir_deg,
                        target_dir_deg=pred_wind_dir_deg,
                        surface_altitude_m=surface_altitude_m,
                        target_altitude_m=target_altitude_m,
                    ),
                }
            )
            converted_features.append(
                {
                    "type": "Feature",
                    "properties": converted_props,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat, round(target_altitude_m, 1)],
                    },
                }
            )

    output_dir = output_root / city_name
    write_json(
        {
            "type": "FeatureCollection",
            "name": f"{city_name}_weather_override",
            "features": converted_features,
        },
        output_dir / "real_weather_field.geojson",
    )
    summary = {
        "city_name": city_name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_weather_path": str(source_path),
        "vertical_model_path": str(model_path),
        "feature_count": len(converted_features),
        "point_count": len(grouped),
        "altitude_levels_m": sorted({altitude_from_feature(feature) for feature in converted_features}),
    }
    write_json(summary, output_dir / "weather_override_summary.json")
    return summary


def main() -> None:
    args = parse_args()
    if not args.model_path.exists():
        raise FileNotFoundError(f"武汉垂直模型不存在：{args.model_path}")
    if not args.city_root.exists():
        raise FileNotFoundError(f"城市资产目录不存在：{args.city_root}")

    summaries = []
    for city_name in list_wuhan_cities(args.city_root, args.city):
        source_path = args.city_root / city_name / "real_weather_field.geojson"
        if not source_path.exists():
            continue
        summaries.append(convert_city_weather(city_name, args.city_root, args.output_root, args.model_path))

    if not summaries:
        raise RuntimeError("没有生成任何武汉场景天气覆盖层。")

    for summary in summaries:
        print(
            f"{summary['city_name']} feature_count={summary['feature_count']} "
            f"altitude_levels_m={summary['altitude_levels_m']} "
            f"output_dir={args.output_root / summary['city_name']}"
        )


if __name__ == "__main__":
    main()
