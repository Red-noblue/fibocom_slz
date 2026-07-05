from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_weather_energy_predictor.feature_builder import build_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build flight-level features from a flights.csv dataset.")
    parser.add_argument("--input", required=True, help="Path to flights.csv")
    parser.add_argument("--output", default="outputs/features.csv", help="Output features CSV path")
    parser.add_argument("--route", default="R1", help="Route id filter, e.g. R1")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_features(args.input, args.output, args.route)
