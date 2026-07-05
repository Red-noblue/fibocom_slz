#!/usr/bin/env bash
# 中文说明：该脚本以 amd64 兼容模式启动 Fibo AI Stack 转换容器，并挂载整个仓库到容器内。

set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

ensure_container_running
docker_run ps --filter "name=${CONTAINER_NAME}" --format 'container={{.Names}} status={{.Status}}'
docker_run exec "${CONTAINER_NAME}" uname -m
docker_run exec "${CONTAINER_NAME}" bash -lc \
  "$(container_snpe_env_prefix); which snpe-onnx-to-dlc; which snpe-dlc-info"
