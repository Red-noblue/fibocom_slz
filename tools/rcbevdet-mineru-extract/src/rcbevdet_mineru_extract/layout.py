# -*- coding: utf-8 -*-
# 路径布局说明：统一解析工具包根目录、默认输出目录和鉴权文件位置，保证整个目录可整体搬迁。
from __future__ import annotations

import os
from pathlib import Path


_TOOLKIT_ROOT_ENV = "RCBEVDET_MINERU_TOOL_ROOT"


def toolkit_root() -> Path:
    env_value = os.environ.get(_TOOLKIT_ROOT_ENV, "").strip()
    if env_value:
        return Path(env_value).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def default_token_file() -> Path:
    return toolkit_root() / "conf" / "keys" / "active.json"


def default_legacy_token_file() -> Path:
    return toolkit_root() / "conf" / "tokens" / "1.md"


def default_output_root() -> Path:
    return toolkit_root() / "out"
