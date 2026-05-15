#!/usr/bin/env bash
# 启动 InfluxDB（Docker）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env_common.sh
source "$SCRIPT_DIR/../env_common.sh"

if ! command -v docker >/dev/null 2>&1; then
  echo "未找到 docker 命令，请先安装 Docker Desktop / Docker Engine。"
  exit 1
fi

mkdir -p "$MQTT_INFLUX_CASE_ROOT/.local/influxdb2"

export INFLUXDB_IMAGE="${INFLUXDB_IMAGE:-influxdb:2}"
export INFLUXDB_HTTP_PORT="${INFLUXDB_HTTP_PORT:-8086}"

echo "InfluxDB OSS v2 镜像: ${INFLUXDB_IMAGE}"
echo "HTTP 端口: ${INFLUXDB_HTTP_PORT} （对应 config.yaml: http://localhost:${INFLUXDB_HTTP_PORT}）"
echo "停止: 在当前终端 Ctrl+C，或另开终端 docker stop mqtt-influxdb-influx2"
echo

cd "$MQTT_INFLUX_SCRIPTS_DIR"
COMPOSE_FILE="docker-compose.influxdb2.yml"
if docker compose version >/dev/null 2>&1; then
  exec docker compose -f "$COMPOSE_FILE" up
fi
if command -v docker-compose >/dev/null 2>&1; then
  exec docker-compose -f "$COMPOSE_FILE" up
fi
echo "需要 Docker Compose（docker compose 或 docker-compose）。请升级 Docker 或安装 compose 插件。"
exit 1