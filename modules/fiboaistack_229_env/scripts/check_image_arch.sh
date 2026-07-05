#!/usr/bin/env bash
# 中文说明：该脚本读取 fiboaistack_229_env 镜像归档元数据，并输出镜像架构与系统信息。

set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

require_tar_file

config_path="$(
  tar -xOf "${FIBO_AISTACK_TAR}" manifest.json | \
    "${PY38_ENV_PYTHON}" -c 'import json,sys; print(json.load(sys.stdin)[0]["Config"])'
)"

tar -xOf "${FIBO_AISTACK_TAR}" "${config_path}" | \
  "${PY38_ENV_PYTHON}" -c '
import json, sys
cfg = json.load(sys.stdin)
print("image_tar=" + sys.argv[1])
print("architecture=" + str(cfg.get("architecture")))
print("os=" + str(cfg.get("os")))
' "${FIBO_AISTACK_TAR}"
