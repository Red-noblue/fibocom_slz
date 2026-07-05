#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"

log() {
  printf '\n[%s] %s\n' "$SCRIPT_NAME" "$*"
}

die() {
  printf '\n[%s] ERROR: %s\n' "$SCRIPT_NAME" "$*" >&2
  exit 1
}

cancel() {
  printf '\n[%s] Canceled.\n' "$SCRIPT_NAME"
  exit 0
}

have() {
  command -v "$1" >/dev/null 2>&1
}

usage() {
  cat <<EOF
Usage:
  ./$SCRIPT_NAME <github-git-url>

Example:
  ./$SCRIPT_NAME https://github.com/Red-noblue/radio-map-estimation-workbench.git
  ./$SCRIPT_NAME git@github.com:Red-noblue/radio-map-estimation-workbench.git

The repository will be cloned into the same directory as this script:
  $SCRIPT_DIR
EOF
}

run_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif have sudo; then
    sudo "$@"
  else
    die "Root privileges are required to install dependencies, but sudo is not available. Install git and gh manually, then rerun."
  fi
}

ensure_sudo_session() {
  if [[ "$(id -u)" -ne 0 ]]; then
    have sudo || die "sudo is required to install dependencies, but it is not available."
    sudo -v
  fi
}

fetch_stdout() {
  local url="$1"
  if have curl; then
    curl -fsSL "$url"
  elif have wget; then
    wget -qO- "$url"
  else
    return 1
  fi
}

install_deps_apt() {
  ensure_sudo_session

  log "Detected apt. Installing git/curl/ca-certificates."
  run_root apt-get update
  run_root env DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates

  if ! have gh; then
    log "Installing the official GitHub CLI apt repository and gh."
    run_root install -d -m 0755 /etc/apt/keyrings
    fetch_stdout "https://cli.github.com/packages/githubcli-archive-keyring.gpg" \
      | run_root tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
    run_root chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg

    local arch
    arch="$(dpkg --print-architecture)"
    printf 'deb [arch=%s signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\n' "$arch" \
      | run_root tee /etc/apt/sources.list.d/github-cli.list >/dev/null

    run_root apt-get update
    run_root env DEBIAN_FRONTEND=noninteractive apt-get install -y gh
  fi
}

install_deps_dnf() {
  ensure_sudo_session

  log "Detected dnf. Installing git and gh."
  run_root dnf install -y git
  if ! have gh; then
    run_root dnf install -y 'dnf-command(config-manager)' || true
    run_root dnf config-manager addrepo --from-repofile=https://cli.github.com/packages/rpm/gh-cli.repo \
      || run_root dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo \
      || true
    run_root dnf install -y gh || run_root dnf install -y github-cli
  fi
}

install_deps_yum() {
  ensure_sudo_session

  log "Detected yum. Installing git and gh."
  run_root yum install -y git yum-utils
  if ! have gh; then
    run_root yum-config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo || true
    run_root yum install -y gh || run_root yum install -y github-cli
  fi
}

install_deps_pacman() {
  ensure_sudo_session

  log "Detected pacman. Installing git and github-cli."
  run_root pacman -Sy --needed --noconfirm git github-cli
}

install_deps_apk() {
  ensure_sudo_session

  log "Detected apk. Installing git and github-cli."
  run_root apk add --no-cache git github-cli
}

install_deps_brew() {
  log "Detected Homebrew. Installing git and gh."
  brew install git gh
}

ensure_dependencies() {
  if have git && have gh; then
    log "Dependencies already exist: git and gh."
    return
  fi

  if have apt-get; then
    install_deps_apt
  elif have dnf; then
    install_deps_dnf
  elif have yum; then
    install_deps_yum
  elif have pacman; then
    install_deps_pacman
  elif have apk; then
    install_deps_apk
  elif have brew; then
    install_deps_brew
  else
    die "Unsupported package manager. Install git and GitHub CLI (gh) manually, then rerun."
  fi

  have git || die "git is not installed or not in PATH."
  have gh || die "gh is not installed or not in PATH."
}

normalize_clone_url() {
  local url="$1"
  local path

  if [[ "$url" == git@github.com:* ]]; then
    path="${url#git@github.com:}"
    path="${path%.git}"
    printf 'https://github.com/%s.git\n' "$path"
    return
  fi

  if [[ "$url" == ssh://git@github.com/* ]]; then
    path="${url#ssh://git@github.com/}"
    path="${path%.git}"
    printf 'https://github.com/%s.git\n' "$path"
    return
  fi

  printf '%s\n' "$url"
}

repo_name_from_url() {
  local url="$1"
  local path name

  path="${url%%\?*}"
  path="${path%%#*}"
  path="${path%/}"
  path="${path#https://github.com/}"
  path="${path#http://github.com/}"
  path="${path#git@github.com:}"
  path="${path#ssh://git@github.com/}"
  path="${path%.git}"
  name="${path##*/}"

  [[ -n "$name" ]] || die "Could not infer repository directory name from URL: $url"
  [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || die "Unsafe repository directory name: $name"
  printf '%s\n' "$name"
}

ensure_github_auth() {
  log "Checking GitHub CLI authentication."
  if gh auth status -h github.com >/dev/null 2>&1; then
    log "GitHub CLI is already authenticated for github.com."
  else
    [[ -t 0 && -t 1 ]] || die "GitHub authentication requires an interactive terminal."
    cat <<'EOF'

GitHub device authorization will start next.
The terminal will show a https://github.com/login/device link and a one-time code.
Open the link in a browser, enter the code, approve access, then return here.
EOF
    gh auth login -h github.com --web --git-protocol https --skip-ssh-key
  fi

  log "Configuring Git to use gh as the HTTPS credential helper."
  gh config set -h github.com git_protocol https >/dev/null
  gh auth setup-git -h github.com >/dev/null
}

confirm_action() {
  local clone_url="$1"
  local dest="$2"

  cat <<EOF

Command to run:
  git clone "$clone_url" "$dest"

Destination:
  $dest
EOF

  local ans
  read -r -p "Continue? [y/N] " ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) cancel ;;
  esac
}

handle_existing_dest() {
  local dest="$1"

  [[ -e "$dest" ]] || return 0

  if [[ -d "$dest/.git" ]]; then
    printf '\nDestination already exists and is a Git repository:\n  %s\n' "$dest"
    local ans
    read -r -p "Run git pull --ff-only instead? [y/N] " ans
    case "$ans" in
      y|Y|yes|YES)
        git -C "$dest" pull --ff-only
        exit 0
        ;;
      *) cancel ;;
    esac
  fi

  die "Destination already exists but is not a Git repository. Refusing to overwrite: $dest"
}

main() {
  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi

  [[ "$#" -eq 1 ]] || {
    usage
    exit 2
  }

  local input_url clone_url repo_name dest
  input_url="$1"
  clone_url="$(normalize_clone_url "$input_url")"
  repo_name="$(repo_name_from_url "$clone_url")"
  dest="$SCRIPT_DIR/$repo_name"

  ensure_dependencies
  ensure_github_auth
  handle_existing_dest "$dest"
  confirm_action "$clone_url" "$dest"

  log "Cloning."
  git clone "$clone_url" "$dest"

  log "Done: $dest"
}

main "$@"
