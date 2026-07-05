# 执行固定路线速度搜索，复用统一候选方案评分接口。
"""执行固定路线速度搜索与消融实验的命令行入口。"""

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

import numpy as np

from uav_energy_engine.config import load_config
from uav_energy_engine.optimize import grid_search_fixed_route_speed, write_speed_search_outputs
from uav_energy_engine.predict import load_defaults_from_features, parse_departure
from uav_energy_engine.schema import BatterySpec, GeoPoint, MissionSpec, VehicleSpec


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="执行固定路线速度搜索。")
    parser.add_argument("--model", default="outputs/model.pkl", help="模型文件路径")
    parser.add_argument("--features", default="outputs/features.csv", help="训练样本 CSV，用于加载默认参数")
    parser.add_argument("--base-config", default="configs/base.yaml", help="基础任务配置")
    parser.add_argument("--weather-config", default="configs/weather.yaml", help="天气配置")
    parser.add_argument("--departure", required=True, help="起飞时间")
    parser.add_argument("--speed-min", type=float, required=True, help="最小速度")
    parser.add_argument("--speed-max", type=float, required=True, help="最大速度")
    parser.add_argument("--speed-step", type=float, required=True, help="速度步长")
    parser.add_argument("--output-csv", default="outputs/speed_search.csv", help="搜索结果 CSV")
    parser.add_argument("--output-json", default="outputs/speed_search.json", help="搜索结果 JSON")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    base_cfg = load_config(args.base_config)
    defaults = load_defaults_from_features(args.features)
    mission = MissionSpec(
        route_name=str(base_cfg["route_name"]),
        start=GeoPoint(lat=float(base_cfg["start"]["lat"]), lon=float(base_cfg["start"]["lon"])),
        end=GeoPoint(lat=float(base_cfg["end"]["lat"]), lon=float(base_cfg["end"]["lon"])),
        departure_time=parse_departure(args.departure),
        step_minutes=int(base_cfg["mission"]["step_minutes"]),
    )
    vehicle = VehicleSpec(
        name=str(base_cfg["vehicle"]["name"]),
        payload_g=defaults["payload_g"],
        cruise_speed_mps=defaults["speed_mps"],
        altitude_m=defaults["altitude_m"],
    )
    battery = BatterySpec(
        capacity_wh=float(base_cfg["battery"]["capacity_wh"]),
        nominal_voltage_v=float(base_cfg["battery"]["nominal_voltage_v"]),
    )
    speeds_mps = np.arange(args.speed_min, args.speed_max + args.speed_step * 0.5, args.speed_step).tolist()
    payload = grid_search_fixed_route_speed(
        model_path=args.model,
        weather_config=args.weather_config,
        mission=mission,
        vehicle=vehicle,
        battery=battery,
        speeds_mps=speeds_mps,
    )
    write_speed_search_outputs(payload, args.output_csv, args.output_json)
    print(json.dumps(payload["best"], indent=2, ensure_ascii=False))
