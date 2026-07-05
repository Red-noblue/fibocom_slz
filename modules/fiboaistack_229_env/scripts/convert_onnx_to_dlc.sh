#!/usr/bin/env bash
# 中文说明：该脚本在本机兼容运行的 Fibo AI Stack 容器内执行 ONNX 到 DLC 的转换，并保存转换日志与 DLC 信息。

set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

if [[ $# -ne 2 ]]; then
  echo "用法：$0 <input.onnx> <output.dlc>" >&2
  exit 1
fi

ensure_module_dirs
ensure_container_running

if [[ ! -f "${QEMU_MUTEX_COMPAT_SO}" ]]; then
  echo "未找到 QEMU mutex 兼容层，开始构建：${QEMU_MUTEX_COMPAT_SO}"
  bash "${MODULE_DIR}/scripts/build_qemu_mutex_compat.sh"
fi

onnx_host="$1"
dlc_host="$2"

if [[ ! -f "${onnx_host}" ]]; then
  echo "未找到 ONNX 文件：${onnx_host}" >&2
  exit 1
fi

mkdir -p "$(dirname "${dlc_host}")"

onnx_container="$(host_to_container_path "${onnx_host}")"
dlc_container="$(host_to_container_path "${dlc_host}")"
info_host="${dlc_host%.dlc}.info.txt"
info_container="$(host_to_container_path "${info_host}")"
log_path="$(latest_log_path onnx_to_dlc)"

echo "开始转换：${onnx_host}"
echo "输出 DLC：${dlc_host}"
echo "日志文件：${log_path}"

docker_run exec "${CONTAINER_NAME}" bash -lc \
  "$(container_snpe_env_prefix); snpe-onnx-to-dlc --input_network '${onnx_container}' --output_path '${dlc_container}'" \
  2>&1 | tee "${log_path}"

docker_run exec "${CONTAINER_NAME}" bash -lc \
  "$(container_snpe_env_prefix); snpe-dlc-info -i '${dlc_container}' > '${info_container}'"

ls -lh "${dlc_host}" "${info_host}"
