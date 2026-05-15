#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== InfluxDB Docker 安装 ==="

if ! command -v docker >/dev/null 2>&1; then
  echo "未找到 docker 命令，请先安装 Docker Desktop。"
  exit 1
fi

INFLUXDB_IMAGE="${INFLUXDB_IMAGE:-influxdb:2}"
INFLUXDB_HTTP_PORT="${INFLUXDB_HTTP_PORT:-8086}"

echo "镜像: $INFLUXDB_IMAGE"
echo "端口: $INFLUXDB_HTTP_PORT"

echo ""
echo "是否确认安装？ (y/n)"
read -r confirm
if [ "$confirm" != "y" ]; then
  echo "取消安装"
  exit 0
fi

mkdir -p "$SCRIPT_DIR/../../.local/influxdb2"

echo ""
echo "启动 InfluxDB..."
cd "$SCRIPT_DIR"
docker compose -f docker-compose.influxdb2.yml up -d

echo ""
echo "InfluxDB 已启动: http://localhost:${INFLUXDB_HTTP_PORT}"
echo "停止: docker compose -f docker-compose.influxdb2.yml down"