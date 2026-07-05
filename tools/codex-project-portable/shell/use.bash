#!/usr/bin/env bash
_cdx_portable_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
_cdx_real_codex="$(command -v codex 2>/dev/null || true)"
export PATH="${_cdx_portable_root}/bin:${PATH}"

codex() {
  local subcommand="${1:-start}"
  case "${subcommand}" in
    ""|start)
      [[ $# -gt 0 ]] && shift
      codex-project start "$@"
      ;;
    -h|--help|help)
      [[ $# -gt 0 ]] && shift
      codex-project help "$@"
      ;;
    -*)
      codex-project start "$@"
      ;;
    resume)
      shift
      codex-project resume "$@"
      ;;
    last)
      shift
      codex-project last "$@"
      ;;
    pick)
      shift
      codex-project pick "$@"
      ;;
    sessions)
      shift
      codex-project sessions "$@"
      ;;
    profiles)
      shift
      codex-project profiles "$@"
      ;;
    exec)
      shift
      codex-project exec "$@"
      ;;
    exec-resume)
      shift
      codex-project exec-resume "$@"
      ;;
    where|doctor|status|repair-state|selftest|runtime|init|pack)
      shift
      codex-project "${subcommand}" "$@"
      ;;
    *)
      if [[ -n "${_cdx_real_codex}" ]]; then
        env -u OPENAI_API_KEY -u OPENAI_BASE_URL -u OPENAI_API_BASE -u OPENAI_ORG_ID -u OPENAI_ORGANIZATION \
          "${_cdx_real_codex}" "$@"
      else
        echo "找不到原始 codex 可执行文件。" >&2
        return 127
      fi
      ;;
  esac
}

cdxraw() {
  if [[ -n "${_cdx_real_codex}" ]]; then
    env -u OPENAI_API_KEY -u OPENAI_BASE_URL -u OPENAI_API_BASE -u OPENAI_ORG_ID -u OPENAI_ORGANIZATION \
      "${_cdx_real_codex}" "$@"
  else
    echo "找不到原始 codex 可执行文件。" >&2
    return 127
  fi
}

cdx() { codex-project start "$@"; }
cdxr() { codex-project resume "$@"; }
cdxl() { codex-project last "$@"; }
cdxp() { codex-project pick "$@"; }
cdxs() { codex-project sessions "$@"; }
cdxd() { codex-project doctor "$@"; }
cdxst() { codex-project status "$@"; }
cdxfix() { codex-project repair-state "$@"; }
cdxcheck() { codex-project selftest "$@"; }
cdxrt() { codex-project runtime "$@"; }
cdxinit() { codex-project init "$@"; }
cdxpack() { codex-project pack "$@"; }
cdxh() { codex-project help "$@"; }
if [[ -z "${CODEX_PORTABLE_NO_AUTO_HELP:-}" ]]; then
  "${_cdx_portable_root}/bin/codex-project" help
fi
