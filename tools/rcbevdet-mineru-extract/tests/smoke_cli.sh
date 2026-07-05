#!/usr/bin/env bash
# 冒烟测试：验证入口脚本、帮助信息和路径解析至少能正常工作，不触发真实抽取任务。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
BIN="${ROOT_DIR}/bin/rcbevdet-mineru-extract"

"${BIN}" paths
"${BIN}" --help >/dev/null
"${BIN}" quota --help >/dev/null
"${BIN}" extract --help >/dev/null

printf 'smoke test ok\n'
