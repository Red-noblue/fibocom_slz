from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_weather_energy_predictor.route_prediction import (
    parse_departure,
    predict_route_energy,
    write_prediction_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict route energy from weather inputs.")
    parser.add_argument("--model", default="outputs/model.pkl")
    parser.add_argument("--features", default="outputs/features.csv")
    parser.add_argument("--route-name", default="BUPT_Haidian_to_Shahe")
    parser.add_argument("--start-lat", type=float, default=39.9598)
    parser.add_argument("--start-lon", type=float, default=116.3520)
    parser.add_argument("--end-lat", type=float, default=40.15608)
    parser.add_argument("--end-lon", type=float, default=116.28333)
    parser.add_argument("--speed-mps", type=float, default=None)
    parser.add_argument("--payload-g", type=float, default=None)
    parser.add_argument("--altitude-m", type=float, default=None)
    parser.add_argument("--battery-wh", type=float, default=130.0)
    parser.add_argument("--departure", required=True)
    parser.add_argument("--step-minutes", type=int, default=1)
    parser.add_argument("--weather-config", default="configs/open_meteo_config.json")
    parser.add_argument("--output-dir", default="outputs/realtime")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = predict_route_energy(
        model_path=args.model,
        features_path=args.features,
        route_name=args.route_name,
        start=(args.start_lat, args.start_lon),
        end=(args.end_lat, args.end_lon),
        speed_mps=args.speed_mps,
        payload_g=args.payload_g,
        altitude_m=args.altitude_m,
        battery_wh=args.battery_wh,
        departure=parse_departure(args.departure),
        step_minutes=args.step_minutes,
        weather_config=args.weather_config,
    )
    write_prediction_outputs(result, args.output_dir)
    print(json.dumps(result.summary, indent=2, ensure_ascii=False))
