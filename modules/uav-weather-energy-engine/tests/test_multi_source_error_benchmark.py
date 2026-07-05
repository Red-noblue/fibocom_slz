# 验证多来源误差基准脚本中的策略辅助特征生成。
"""验证多来源误差基准脚本。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_multi_source_error_benchmark as benchmark


def test_phase_interaction_features_are_generated():
    """阶段交互特征应能表达数据源和阶段的组合。"""

    frame = pd.DataFrame(
        {
            "source_dataset": ["m100", "wemuav"],
            "phase_label": ["hover_or_slow", "cruise"],
            "source_is_m100": [1.0, 0.0],
            "source_is_wemuav": [0.0, 1.0],
        }
    )

    out = benchmark._with_auxiliary_strategy_columns(frame)

    assert float(out["phase_is_hover_or_slow"].iloc[0]) == 1.0
    assert float(out["source_is_m100_x_phase_is_hover_or_slow"].iloc[0]) == 1.0
    assert float(out["source_is_wemuav_x_phase_is_cruise"].iloc[1]) == 1.0
    assert out["source_phase_key"].tolist() == ["m100|hover_or_slow", "wemuav|cruise"]
