# 读取统一任务配置，执行固定航线速度搜索，服务后续主动调度。
"""执行任务级速度搜索入口。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np

from uav_energy_engine.optimize import grid_search_fixed_route_speed, write_speed_search_outputs
from uav_energy_engine.task_io import load_task_bundle


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _resolve_model_and_features(model_arg: str, features_arg: str | None) -> tuple[Path, Path]:
    """支持传模型目录，自动定位模型和训练特征表。"""

    model_path = _resolve_path(model_arg)
    if model_path.is_dir():
        resolved_model = model_path / "model.pkl"
        resolved_features = _resolve_path(features_arg) if features_arg else model_path / "train_frame.csv"
    else:
        resolved_model = model_path
        resolved_features = _resolve_path(features_arg) if features_arg else ROOT / "outputs/features.csv"
    return resolved_model, resolved_features


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="执行统一任务配置速度搜索。")
    parser.add_argument("--model", default="outputs/model.pkl", help="模型文件路径，或包含 model.pkl 的模型目录")
    parser.add_argument("--features", default=None, help="训练样本 CSV；若 model 为目录则默认读取 train_frame.csv")
    parser.add_argument("--task-config", required=True, help="任务配置 JSON/YAML")
    parser.add_argument("--weather-config", default="configs/weather.yaml", help="天气配置")
    parser.add_argument("--speed-min", type=float, required=True, help="最小速度")
    parser.add_argument("--speed-max", type=float, required=True, help="最大速度")
    parser.add_argument("--speed-step", type=float, required=True, help="速度步长")
    parser.add_argument("--output-csv", default="outputs/task_speed_search/results.csv", help="搜索结果 CSV")
    parser.add_argument("--output-json", default="outputs/task_speed_search/summary.json", help="搜索结果 JSON")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    model_path, features_path = _resolve_model_and_features(args.model, args.features)
    mission, vehicle, battery, task_cfg = load_task_bundle(args.task_config, features_path)
    speeds_mps = np.arange(args.speed_min, args.speed_max + args.speed_step * 0.5, args.speed_step).tolist()
    payload = grid_search_fixed_route_speed(
        model_path=model_path,
        weather_config=args.weather_config,
        mission=mission,
        vehicle=vehicle,
        battery=battery,
        speeds_mps=speeds_mps,
    )
    payload["task_config"] = str(_resolve_path(args.task_config).resolve())
    payload["task"] = task_cfg
    write_speed_search_outputs(payload, _resolve_path(args.output_csv), _resolve_path(args.output_json))
    print(json.dumps(payload["best"], indent=2, ensure_ascii=False))
