from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_gis_replay_studio.map_renderer import load_prediction_artifacts, render_prediction_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a GIS route map from prediction artifacts.")
    parser.add_argument("--summary", required=True, help="Path to realtime_route_summary.json")
    parser.add_argument("--timeseries", required=True, help="Path to realtime_route_timeseries.csv")
    parser.add_argument("--output", default="outputs/realtime_route_map.html", help="Output HTML path")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    summary, step_rows = load_prediction_artifacts(args.summary, args.timeseries)
    render_prediction_map(summary, step_rows, args.output)
