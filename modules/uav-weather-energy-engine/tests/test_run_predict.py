"""验证正式预测脚本的路径与航线点解析。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_predict


def test_resolve_model_and_features_supports_model_directory(tmp_path: Path):
    """传入模型目录时，应默认定位其中的模型与训练表。"""

    model_dir = tmp_path / "deployment_model_default"
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path, features_path = run_predict.resolve_model_and_features(str(model_dir), None)

    assert model_path == model_dir / "model.pkl"
    assert features_path == model_dir / "train_frame.csv"


def test_parse_route_points_reads_polyline_json(tmp_path: Path):
    """预测脚本应能读取折线航线点 JSON。"""

    route_json = tmp_path / "route_points.json"
    route_json.write_text(
        json.dumps(
            [
                {"lat": 39.0, "lon": 116.0, "alt_m": 30.0},
                {"lat": 39.001, "lon": 116.0, "alt_m": 40.0},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    points = run_predict.parse_route_points(str(route_json))

    assert len(points) == 2
    assert round(float(points[0].lat), 6) == 39.0
    assert round(float(points[1].alt_m), 6) == 40.0
