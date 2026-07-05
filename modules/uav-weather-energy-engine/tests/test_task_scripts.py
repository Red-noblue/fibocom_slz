"""验证任务级脚本的路径解析辅助逻辑。"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_task_predict
import run_task_speed_search


def test_run_task_predict_resolves_model_directory(tmp_path: Path):
    """任务级预测脚本应支持直接传模型目录。"""

    model_dir = tmp_path / "deployment_model_default"
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path, features_path = run_task_predict._resolve_model_and_features(str(model_dir), None)

    assert model_path == model_dir / "model.pkl"
    assert features_path == model_dir / "train_frame.csv"


def test_run_task_speed_search_resolves_model_directory(tmp_path: Path):
    """任务级速度搜索脚本也应支持直接传模型目录。"""

    model_dir = tmp_path / "deployment_model_default"
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path, features_path = run_task_speed_search._resolve_model_and_features(str(model_dir), None)

    assert model_path == model_dir / "model.pkl"
    assert features_path == model_dir / "train_frame.csv"
