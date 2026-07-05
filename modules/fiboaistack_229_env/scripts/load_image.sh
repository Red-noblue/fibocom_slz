#!/usr/bin/env bash
# 中文说明：该脚本将本机上的 fiboaistack_229_env 镜像归档导入 Docker，并记录加载日志。

set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

require_tar_file
ensure_module_dirs

log_path="$(latest_log_path docker_load)"
echo "开始加载镜像：${FIBO_AISTACK_TAR}"
echo "日志文件：${log_path}"

docker_run load -i "${FIBO_AISTACK_TAR}" | tee "${log_path}"
docker_run image inspect "${IMAGE_NAME}" --format 'loaded_image={{.RepoTags}} arch={{.Architecture}} os={{.Os}}'
