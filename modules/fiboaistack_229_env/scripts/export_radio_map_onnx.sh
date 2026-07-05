#!/usr/bin/env bash
# 中文说明：该脚本使用本机 py3.8 部署环境导出无线电地图模型 ONNX，并保存到本模块 inputs 目录。

set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

ensure_module_dirs

if [[ ! -x "${PY38_ENV_PYTHON}" ]]; then
  echo "未找到 py3.8 部署环境解释器：${PY38_ENV_PYTHON}" >&2
  exit 1
fi

out_path="${MODULE_DIR}/inputs/radio_map_liteunet.onnx"

(
  cd "${RADIO_MAP_UPSTREAM}"
  "${PY38_ENV_PYTHON}" modules/m4/tools/export_onnx.py "${RADIO_MAP_RUN_ID}" "${out_path}"
)

ls -lh "${out_path}"
