"""读取本模块配置文件。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

import yaml


def load_config(path: Union[str, Path]) -> Dict[str, Any]:
    """按后缀读取 JSON 或 YAML 配置。"""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    if config_path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if config_path.suffix.lower() == ".json":
        return json.loads(config_path.read_text(encoding="utf-8"))
    raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
