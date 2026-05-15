#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Mosquitto Docker 安装 ==="

if ! command -v docker >/dev/null 2>&1; then
  echo "未找到 docker 命令，请先安装 Docker Desktop。"
  exit 1
fi

MOSQUITTO_IMAGE="${MOSQUITTO_IMAGE:-eclipse-mosquitto:2}"
MOSQUITTO_PORT="${MOSQUITTO_PORT:-1883}"

echo "镜像: $MOSQUITTO_IMAGE"
echo "端口: $MOSQUITTO_PORT"

echo ""
echo "是否确认安装？ (y/n)"
read -r confirm
if [ "$confirm" != "y" ]; then
  echo "取消安装"
  exit 0
fi

mkdir -p "$SCRIPT_DIR/../../.local/mosquitto/config"
mkdir -p "$SCRIPT_DIR/../../.local/mosquitto/data"
mkdir -p "$SCRIPT_DIR/../../.local/mosquitto/log"

if [ ! -f "$SCRIPT_DIR/../../.local/mosquitto/config/mosquitto.conf" ]; then
  cat > "$SCRIPT_DIR/../../.local/mosquitto/config/mosquitto.conf" <<'EOF'
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest stdout
EOF
fi

echo ""
echo "启动 Mosquitto..."
docker run -d \
  --name mosquitto \
  -p "$MOSQUITTO_PORT:1883" \
  -v "$SCRIPT_DIR/../../.local/mosquitto/config/mosquitto.conf:/mosquitto/config/mosquitto.conf" \
  -v "$SCRIPT_DIR/../../.local/mosquitto/data:/mosquitto/data" \
  -v "$SCRIPT_DIR/../../.local/mosquitto/log:/mosquitto/log" \
  "$MOSQUITTO_IMAGE"

echo ""
echo "Mosquitto 已启动: tcp://localhost:${MOSQUITTO_PORT}"
echo "停止: docker stop mosquitto && docker rm mosquitto"