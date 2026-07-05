#!/usr/bin/env bash
# 中文说明：该脚本在 Fibo AI Stack amd64 容器内编译 QEMU mutex 兼容层，用于测试 Qualcomm 转换工具启动问题。

set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

ensure_module_dirs
ensure_container_running

shim_src="${MODULE_DIR}/shims/qemu_pthread_mutex_compat.c"
shim_out="${MODULE_DIR}/shims/qemu_pthread_mutex_compat.so"
shim_src_container="$(host_to_container_path "${shim_src}")"
shim_out_container="$(host_to_container_path "${shim_out}")"

if [[ ! -f "${shim_src}" ]]; then
  echo "未找到兼容层源码：${shim_src}" >&2
  exit 1
fi

docker_run exec "${CONTAINER_NAME}" bash -lc \
  "gcc -shared -fPIC -O2 -Wall -Wextra '${shim_src_container}' -ldl -o '${shim_out_container}'"

ls -lh "${shim_out}"
