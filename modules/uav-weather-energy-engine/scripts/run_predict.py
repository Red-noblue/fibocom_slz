# 执行固定路线固定航速预测，并优先保持推理步长与训练分段一致。
"""执行固定路线固定航速预测的命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_energy_engine.config import load_config
from uav_energy_engine.predict import (
    load_defaults_from_features,
    parse_departure,
    predict_fixed_route_energy,
    write_prediction_outputs,
)
from uav_energy_engine.schema import BatterySpec, GeoPoint, MissionSpec, VehicleSpec


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def resolve_model_and_features(model_arg: str, features_arg: str | None) -> tuple[Path, Path]:
    """支持直接传模型目录，而不是只传 model.pkl。"""

    model_path = _resolve_path(model_arg)
    if model_path.is_dir():
        resolved_model = model_path / "model.pkl"
        resolved_features = _resolve_path(features_arg) if features_arg else model_path / "train_frame.csv"
    else:
        resolved_model = model_path
        resolved_features = _resolve_path(features_arg) if features_arg else ROOT / "outputs/features.csv"
    return resolved_model, resolved_features


def vehicle_value(args_value, base_cfg: dict, defaults: dict, key: str, default_key: str | None = None):
    """按命令行、基础配置、训练样本默认值的优先级读取车辆参数。"""

    if args_value is not None:
        return args_value
    if "vehicle" in base_cfg and key in base_cfg["vehicle"]:
        return float(base_cfg["vehicle"][key])
    lookup_key = default_key or key
    if lookup_key in defaults:
        return defaults[lookup_key]
    if key == "payload_g" and "payload_kg" in defaults:
        return float(defaults["payload_kg"]) * 1000.0
    raise KeyError(f"缺少车辆默认参数: {lookup_key}")


def mission_step_minutes(args_value, base_cfg: dict, defaults: dict) -> int:
    """按命令行、训练样本分段、基础配置的优先级读取预测步长。"""

    if args_value is not None:
        return int(args_value)
    if "step_minutes" in defaults:
        return int(defaults["step_minutes"])
    return int(base_cfg["mission"]["step_minutes"])


def parse_route_points(path: str | None) -> list[GeoPoint]:
    """从 JSON 文件读取折线航线点。"""

    if not path:
        return []
    payload = json.loads(_resolve_path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("route-points-json 必须是点位数组。")
    points = []
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("route-points-json 中每个点必须是对象。")
        points.append(
            GeoPoint(
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                alt_m=float(row.get("alt_m", 0.0)),
            )
        )
    return points


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="执行固定路线固定航速天气能耗预测。")
    parser.add_argument("--model", default="outputs/model.pkl", help="模型文件路径，或包含 model.pkl 的模型目录")
    parser.add_argument("--features", default=None, help="训练样本 CSV，用于加载默认参数；若 model 是目录则默认读取 train_frame.csv")
    parser.add_argument("--base-config", default="configs/base.yaml", help="基础任务配置")
    parser.add_argument("--weather-config", default="configs/weather.yaml", help="天气配置")
    parser.add_argument("--route-name", default=None, help="覆盖路线名称")
    parser.add_argument("--route-points-json", default=None, help="折线航线点 JSON 文件")
    parser.add_argument("--start-lat", type=float, default=None)
    parser.add_argument("--start-lon", type=float, default=None)
    parser.add_argument("--end-lat", type=float, default=None)
    parser.add_argument("--end-lon", type=float, default=None)
    parser.add_argument("--speed-mps", type=float, default=None)
    parser.add_argument("--payload-g", type=float, default=None)
    parser.add_argument("--altitude-m", type=float, default=None)
    parser.add_argument("--battery-wh", type=float, default=None)
    parser.add_argument("--departure", required=True, help="起飞时间")
    parser.add_argument("--step-minutes", type=int, default=None)
    parser.add_argument("--safety-profile", default=None, help="保守可达性校准 JSON；不填则只输出点预测")
    parser.add_argument("--output-dir", default="outputs/predict", help="预测输出目录")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    model_path, features_path = resolve_model_and_features(args.model, args.features)
    base_cfg = load_config(args.base_config)
    defaults = load_defaults_from_features(features_path)
    route_points = parse_route_points(args.route_points_json)

    mission = MissionSpec(
        route_name=args.route_name or base_cfg["route_name"],
        start=GeoPoint(
            lat=args.start_lat if args.start_lat is not None else float(base_cfg["start"]["lat"]),
            lon=args.start_lon if args.start_lon is not None else float(base_cfg["start"]["lon"]),
        ),
        end=GeoPoint(
            lat=args.end_lat if args.end_lat is not None else float(base_cfg["end"]["lat"]),
            lon=args.end_lon if args.end_lon is not None else float(base_cfg["end"]["lon"]),
        ),
        departure_time=parse_departure(args.departure),
        step_minutes=mission_step_minutes(args.step_minutes, base_cfg, defaults),
        route_points=route_points,
    )
    vehicle = VehicleSpec(
        name=str(base_cfg["vehicle"]["name"]),
        payload_g=vehicle_value(args.payload_g, base_cfg, defaults, "payload_g"),
        cruise_speed_mps=vehicle_value(args.speed_mps, base_cfg, defaults, "cruise_speed_mps", "speed_mps"),
        altitude_m=vehicle_value(args.altitude_m, base_cfg, defaults, "altitude_m"),
    )
    battery = BatterySpec(
        capacity_wh=args.battery_wh if args.battery_wh is not None else float(base_cfg["battery"]["capacity_wh"]),
        nominal_voltage_v=float(base_cfg["battery"]["nominal_voltage_v"]),
    )

    bundle = predict_fixed_route_energy(
        model_path=model_path,
        weather_config=args.weather_config,
        mission=mission,
        vehicle=vehicle,
        battery=battery,
        safety_profile=args.safety_profile,
    )
    write_prediction_outputs(bundle, args.output_dir)
    print(json.dumps(bundle.summary, indent=2, ensure_ascii=False))
