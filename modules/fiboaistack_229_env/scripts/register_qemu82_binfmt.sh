#!/usr/bin/env bash
# 中文说明：将标准 qemu-x86_64 binfmt 重新注册到 QEMU 8.2.2，用于规避旧 QEMU 4.2.1 在量化阶段的 SIGILL。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_QEMU="${TARGET_QEMU:-/usr/local/bin/qemu-x86_64-static-8.2.2}"
MODULE_QEMU="${MODULE_DIR}/tmp_qemu_pkg/pkg/extract/usr/bin/qemu-x86_64-static"

if [[ ! -x "${TARGET_QEMU}" ]]; then
  if [[ ! -f "${MODULE_QEMU}" ]]; then
    echo "未找到 QEMU 8.2.2：${TARGET_QEMU}" >&2
    echo "也未找到模块内备份：${MODULE_QEMU}" >&2
    exit 1
  fi
  echo "安装 QEMU 8.2.2 到 ${TARGET_QEMU}"
  sudo install -m 0755 "${MODULE_QEMU}" "${TARGET_QEMU}"
fi

version="$("${TARGET_QEMU}" --version 2>/dev/null | head -n 1 || true)"
echo "使用解释器：${TARGET_QEMU}"
echo "版本：${version}"
if [[ "${version}" != *"8.2.2"* ]]; then
  echo "目标解释器不是已验证的 QEMU 8.2.2，停止注册。" >&2
  exit 2
fi

if [[ ! -w /proc/sys/fs/binfmt_misc/register ]]; then
  echo "需要 sudo 权限写入 binfmt_misc。"
fi

if [[ -e /proc/sys/fs/binfmt_misc/qemu-x86_64 ]]; then
  echo "禁用旧 qemu-x86_64 binfmt"
  echo -1 | sudo tee /proc/sys/fs/binfmt_misc/qemu-x86_64 >/dev/null
fi

echo "注册 qemu-x86_64 -> ${TARGET_QEMU}"
printf '%s\n' ":qemu-x86_64:M::\\x7f\\x45\\x4c\\x46\\x02\\x01\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x02\\x00\\x3e\\x00:\\xff\\xff\\xff\\xff\\xff\\xfe\\xfe\\xfc\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xfe\\xff\\xff\\xff:${TARGET_QEMU}:OCF" \
  | sudo tee /proc/sys/fs/binfmt_misc/register >/dev/null

echo "注册结果："
cat /proc/sys/fs/binfmt_misc/qemu-x86_64
