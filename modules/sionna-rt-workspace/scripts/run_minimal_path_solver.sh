#!/usr/bin/env bash
# 本脚本用于从项目根目录运行 Sionna RT 最小复现脚本。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/._envs/sionna-rt-py310/bin/python"

"${PYTHON_BIN}" "${ROOT_DIR}/modules/sionna-rt-workspace/scripts/minimal_path_solver.py" "$@"
