#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== nanoMQ Docker 安装 ==="

if ! command -v docker >/dev/null 2>&1; then
  echo "未找到 docker 命令，请先安装 Docker Desktop。"
  exit 1
fi

NANOMQ_IMAGE="${NANOMQ_IMAGE:-emqx/nanomq:0.24.13}"
NANOMQ_TCP_PORT="${NANOMQ_TCP_PORT:-1883}"
NANOMQ_HTTP_PORT="${NANOMQ_HTTP_PORT:-8081}"

echo "镜像: $NANOMQ_IMAGE"
echo "TCP 端口: $NANOMQ_TCP_PORT"
echo "HTTP 端口: $NANOMQ_HTTP_PORT"

echo ""
echo "是否确认安装？ (y/n)"
read -r confirm
if [ "$confirm" != "y" ]; then
  echo "取消安装"
  exit 0
fi

mkdir -p "$SCRIPT_DIR/../../.local/nanomq"

echo ""
echo "启动 nanoMQ..."
docker run -d \
  --name nanomq \
  -p "$NANOMQ_TCP_PORT:1883" \
  -p "$NANOMQ_HTTP_PORT:8081" \
  -v "$SCRIPT_DIR/../../.local/nanomq/config:/etc/nanomq" \
  "$NANOMQ_IMAGE"

echo ""
echo "nanoMQ 已启动: tcp://localhost:${NANOMQ_TCP_PORT}"
echo "停止: docker stop nanomq && docker rm nanomq"