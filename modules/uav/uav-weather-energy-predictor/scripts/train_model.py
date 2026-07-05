from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_weather_energy_predictor.training import train_energy_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the weather-to-energy demo model.")
    parser.add_argument("--features", default="outputs/features.csv", help="Features CSV path")
    parser.add_argument("--model-out", default="outputs/model.pkl", help="Model output path")
    parser.add_argument("--metrics-out", default="outputs/metrics.json", help="Metrics JSON path")
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train_energy_model(args.features, args.model_out, args.metrics_out, args.random_state)
