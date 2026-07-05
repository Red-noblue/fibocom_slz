#!/usr/bin/env bash
# 环境测量硬件网页启动脚本，负责启动可视化服务并保留普通用户 Python 包路径。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${1:-0.0.0.0}"
PORT="${2:-18080}"
USER_SITE_PACKAGES="$(python3 - <<'PY'
import os
import pwd
import site

sudo_user = os.environ.get("SUDO_USER")
if sudo_user:
    home = pwd.getpwnam(sudo_user).pw_dir
    version = f"{os.sys.version_info.major}.{os.sys.version_info.minor}"
    print(os.path.join(home, ".local", "lib", f"python{version}", "site-packages"))
else:
    print(site.getusersitepackages())
PY
)"
PYTHONPATH_VALUE="${ROOT_DIR}/src:${USER_SITE_PACKAGES}${PYTHONPATH:+:${PYTHONPATH}}"

exec env PYTHONPATH="${PYTHONPATH_VALUE}" \
  python3 -m uvicorn environmental_sensing_hardware.web.app:app \
  --host "${HOST}" \
  --port "${PORT}"
