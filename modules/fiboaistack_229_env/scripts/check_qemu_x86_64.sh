#!/usr/bin/env bash
# 中文说明：检查当前 x86_64 binfmt 与 QEMU 版本，辅助判断 Fibo AI Stack amd64 容器是否会命中旧 QEMU。

set -euo pipefail

print_qemu_version() {
  local bin="$1"
  if [[ -x "${bin}" ]]; then
    "${bin}" --version 2>/dev/null | head -n 1 || true
  else
    echo "not executable: ${bin}"
  fi
}

print_binfmt_entry() {
  local name="$1"
  local path="/proc/sys/fs/binfmt_misc/${name}"
  echo "## ${name}"
  if [[ ! -r "${path}" ]]; then
    echo "missing or unreadable: ${path}"
    return
  fi
  cat "${path}"
  local interp
  interp="$(awk '/^interpreter / {print $2}' "${path}")"
  if [[ -n "${interp}" ]]; then
    echo "version: $(print_qemu_version "${interp}")"
  fi
}

echo "## qemu binaries"
print_qemu_version /usr/bin/qemu-x86_64-static
print_qemu_version /usr/local/bin/qemu-x86_64-static-8.2.2
echo
print_binfmt_entry qemu-x86_64
echo
print_binfmt_entry codex-qemu-x86_64

canonical_interp="$(awk '/^interpreter / {print $2}' /proc/sys/fs/binfmt_misc/qemu-x86_64 2>/dev/null || true)"
if [[ "${canonical_interp}" != "/usr/local/bin/qemu-x86_64-static-8.2.2" ]]; then
  echo
  echo "WARNING: canonical qemu-x86_64 does not point to QEMU 8.2.2."
  echo "Run: modules/fiboaistack_229_env/scripts/register_qemu82_binfmt.sh"
fi
