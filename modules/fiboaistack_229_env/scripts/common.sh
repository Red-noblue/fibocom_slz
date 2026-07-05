#!/usr/bin/env bash
# 中文说明：该脚本提供 fiboaistack_229_env 模块的公共路径解析与 Docker 调用辅助函数。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MODULE_DIR}/../.." && pwd)"

FIBO_AISTACK_TAR="${FIBO_AISTACK_TAR:-/home/fibo/fiboaistack_229_env.tar}"
IMAGE_NAME="${IMAGE_NAME:-fiboaistack_229_env:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-fiboaistack_229_env_amd64}"
CONTAINER_WORKDIR="${CONTAINER_WORKDIR:-/workspace}"
CONTAINER_SNPE_ROOT="${CONTAINER_SNPE_ROOT:-/opt/2.29.0.241129}"
CONTAINER_SNPE_BIN_DIR="${CONTAINER_SNPE_BIN_DIR:-/opt/2.29.0.241129/bin/x86_64-linux-clang}"
CONTAINER_PY310_ENV="${CONTAINER_PY310_ENV:-/opt/python310_env}"
QEMU_MUTEX_COMPAT_SO="${QEMU_MUTEX_COMPAT_SO:-${MODULE_DIR}/shims/qemu_pthread_mutex_compat.so}"
PY38_ENV_PYTHON="${PY38_ENV_PYTHON:-${REPO_ROOT}/._envs/radio-map-qcs6490-py38/bin/python}"
RADIO_MAP_UPSTREAM="${RADIO_MAP_UPSTREAM:-${REPO_ROOT}/modules/radio-map-estimation-workbench}"
RADIO_MAP_RUN_ID="${RADIO_MAP_RUN_ID:-m4-1_aspp_base48_focus_bg_edge_losaware_y133p129_3k_s17_cleanproto}"

ensure_module_dirs() {
  mkdir -p "${MODULE_DIR}/inputs" "${MODULE_DIR}/outputs" "${MODULE_DIR}/logs"
}

docker_run() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
    return
  fi
  if sudo -n docker info >/dev/null 2>&1; then
    sudo -n docker "$@"
    return
  fi
  sudo docker "$@"
}

latest_log_path() {
  local prefix="$1"
  ensure_module_dirs
  printf '%s/logs/%s_%s.log\n' "${MODULE_DIR}" "${prefix}" "$(date +%Y%m%d_%H%M%S)"
}

require_tar_file() {
  if [[ ! -f "${FIBO_AISTACK_TAR}" ]]; then
    echo "未找到镜像归档：${FIBO_AISTACK_TAR}" >&2
    exit 1
  fi
}

require_loaded_image() {
  if ! docker_run image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    echo "镜像未加载：${IMAGE_NAME}" >&2
    echo "请先执行：${MODULE_DIR}/scripts/load_image.sh" >&2
    exit 1
  fi
}

warn_if_old_qemu_x86_64() {
  local entry="/proc/sys/fs/binfmt_misc/qemu-x86_64"
  local expected="/usr/local/bin/qemu-x86_64-static-8.2.2"
  if [[ ! -r "${entry}" ]]; then
    return
  fi
  local interp
  interp="$(awk '/^interpreter / {print $2}' "${entry}")"
  if [[ -n "${interp}" && "${interp}" != "${expected}" ]]; then
    echo "WARNING: qemu-x86_64 binfmt 当前指向 ${interp}，量化阶段可能触发 QEMU Illegal instruction。" >&2
    echo "建议执行：${MODULE_DIR}/scripts/register_qemu82_binfmt.sh" >&2
  fi
}

ensure_container_running() {
  require_loaded_image
  warn_if_old_qemu_x86_64
  if docker_run ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    return
  fi
  if docker_run ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    docker_run start "${CONTAINER_NAME}" >/dev/null
    return
  fi
  docker_run run \
    --platform linux/amd64 \
    -itd \
    --name "${CONTAINER_NAME}" \
    --workdir "${CONTAINER_WORKDIR}" \
    -v "${REPO_ROOT}:${CONTAINER_WORKDIR}" \
    "${IMAGE_NAME}" \
    bash >/dev/null
}

host_to_container_path() {
  local host_path
  host_path="$(realpath "$1")"
  if [[ "${host_path}" != "${REPO_ROOT}"* ]]; then
    echo "路径不在仓库内，无法映射到容器：${host_path}" >&2
    exit 1
  fi
  local rel="${host_path#${REPO_ROOT}/}"
  printf '%s/%s\n' "${CONTAINER_WORKDIR}" "${rel}"
}

container_snpe_env_prefix() {
  local py310_activate="${CONTAINER_PY310_ENV}/bin/activate"
  local env_prefix
  printf -v env_prefix 'source %q; export SNPE_ROOT=%q QNN_SDK_ROOT=%q PATH=%q:$PATH LD_LIBRARY_PATH=%q:$LD_LIBRARY_PATH PYTHONPATH=%q:$PYTHONPATH' \
    "${py310_activate}" \
    "${CONTAINER_SNPE_ROOT}" \
    "${CONTAINER_SNPE_ROOT}" \
    "${CONTAINER_SNPE_BIN_DIR}" \
    "${CONTAINER_SNPE_ROOT}/lib" \
    "${CONTAINER_SNPE_ROOT}/lib/python"
  if [[ -f "${QEMU_MUTEX_COMPAT_SO}" ]]; then
    local shim_container
    shim_container="$(host_to_container_path "${QEMU_MUTEX_COMPAT_SO}")"
    env_prefix="${env_prefix}; export LD_PRELOAD=${shim_container}\${LD_PRELOAD:+:\$LD_PRELOAD}"
  fi
  printf '%s' "${env_prefix}"
}
