# -*- coding: utf-8 -*-
# 模块入口：允许通过 `python -m rcbevdet_mineru_extract` 直接调用命令行。
from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
