#!/usr/bin/env bash
# 无人机虚拟验证 Web 工作台一键启动脚本：用于在开发板或普通 Linux 主机上启动、停止和检查服务。

set -euo pipefail

FIBOCOM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${UAV_APP_DIR:-$FIBOCOM_ROOT/modules/uav_virtual_validation}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${UAV_WEB_HOST:-0.0.0.0}"
PORT="${UAV_WEB_PORT:-8090}"
PID_FILE="${UAV_WEB_PID_FILE:-$APP_DIR/outputs/web_server.pid}"
LOG_FILE="${UAV_WEB_LOG_FILE:-$APP_DIR/outputs/web_server.log}"

detect_ip() {
  local first_ip
  first_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [ -n "$first_ip" ]; then
    printf '%s\n' "$first_ip"
  else
    printf '127.0.0.1\n'
  fi
}

PUBLIC_IP="${UAV_WEB_PUBLIC_IP:-$(detect_ip)}"

usage() {
  cat <<EOF
用法：
  $0 [start|foreground|stop|restart|status]

默认动作：
  start       后台启动 Web 服务

环境变量：
  UAV_WEB_HOST       默认 0.0.0.0
  UAV_WEB_PORT       默认 8090
  UAV_WEB_PUBLIC_IP  默认自动检测
  PYTHON_BIN         默认 python3
  UAV_APP_DIR        默认 <fibocom_slz>/modules/uav_virtual_validation

示例：
  $0
  $0 status
  UAV_WEB_PORT=8091 $0 restart
  $0 foreground
EOF
}

server_cmd() {
  printf '%s\n' "$PYTHON_BIN $APP_DIR/scripts/serve_web.py --host $HOST --port $PORT --public-ip $PUBLIC_IP"
}

pid_value() {
  if [ -f "$PID_FILE" ]; then
    cat "$PID_FILE"
  fi
}

is_our_server() {
  local pid="$1"
  local cmd
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    return 1
  fi
  cmd="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  case "$cmd" in
    *"uav_virtual_validation/scripts/serve_web.py"*) return 0 ;;
    *) return 1 ;;
  esac
}

ensure_ready() {
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "错误：找不到 Python 解释器：$PYTHON_BIN" >&2
    exit 1
  fi
  if [ ! -f "$APP_DIR/scripts/serve_web.py" ]; then
    echo "错误：找不到服务脚本：$APP_DIR/scripts/serve_web.py" >&2
    exit 1
  fi
  if [ ! -f "$APP_DIR/outputs/real_city/manhattan_midtown/city_summary.json" ]; then
    echo "警告：未找到 Manhattan 城市摘要，页面可能无法加载默认真实城市。" >&2
  fi
  mkdir -p "$APP_DIR/outputs"
}

print_urls() {
  echo "本机访问：    http://127.0.0.1:$PORT/"
  echo "开发板访问：  http://$PUBLIC_IP:$PORT/"
  echo "日志文件：    $LOG_FILE"
  echo "PID 文件：    $PID_FILE"
}

start_background() {
  ensure_ready
  local pid
  pid="$(pid_value || true)"
  if is_our_server "$pid"; then
    echo "服务已经在运行：PID $pid"
    print_urls
    return
  fi
  echo "启动服务：$(server_cmd)"
  nohup "$PYTHON_BIN" "$APP_DIR/scripts/serve_web.py" \
    --host "$HOST" \
    --port "$PORT" \
    --public-ip "$PUBLIC_IP" \
    > "$LOG_FILE" 2>&1 &
  pid="$!"
  echo "$pid" > "$PID_FILE"
  sleep 1
  if ! is_our_server "$pid"; then
    echo "错误：服务启动失败，最近日志如下：" >&2
    tail -n 40 "$LOG_FILE" >&2 || true
    exit 1
  fi
  echo "服务已启动：PID $pid"
  print_urls
}

start_foreground() {
  ensure_ready
  echo "前台启动服务：$(server_cmd)"
  print_urls
  exec "$PYTHON_BIN" "$APP_DIR/scripts/serve_web.py" \
    --host "$HOST" \
    --port "$PORT" \
    --public-ip "$PUBLIC_IP"
}

stop_server() {
  local pid
  pid="$(pid_value || true)"
  if is_our_server "$pid"; then
    kill "$pid"
    rm -f "$PID_FILE"
    echo "已停止服务：PID $pid"
    return
  fi
  echo "未发现由本脚本记录的运行中服务。"
}

status_server() {
  local pid
  pid="$(pid_value || true)"
  if is_our_server "$pid"; then
    echo "服务运行中："
    ps -p "$pid" -o pid,ppid,stat,%cpu,%mem,rss,etime,args
    print_urls
  else
    echo "服务未运行。"
  fi
}

ACTION="${1:-start}"
case "$ACTION" in
  start) start_background ;;
  foreground) start_foreground ;;
  stop) stop_server ;;
  restart) stop_server; start_background ;;
  status) status_server ;;
  -h|--help|help) usage ;;
  *)
    usage
    exit 1
    ;;
esac
