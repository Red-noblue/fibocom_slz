from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_gis_replay_studio.map_renderer import load_prediction_artifacts
from uav_gis_replay_studio.site_builder import build_static_site


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a static website from UAV prediction artifacts.")
    parser.add_argument("--summary", required=True, help="Path to realtime_route_summary.json")
    parser.add_argument("--timeseries", required=True, help="Path to realtime_route_timeseries.csv")
    parser.add_argument("--output-dir", default="outputs/site", help="Static site output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    summary, step_rows = load_prediction_artifacts(args.summary, args.timeseries)
    index_path = build_static_site(summary, step_rows, args.output_dir)
    print(f"site entry generated at: {index_path}")
