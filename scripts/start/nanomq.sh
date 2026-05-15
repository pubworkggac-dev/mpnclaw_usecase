#!/usr/bin/env bash
# 启动 nanoMQ
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env_common.sh
source "$SCRIPT_DIR/../env_common.sh"

NANOMQ_TCP_HOST="${NANOMQ_TCP_HOST:-127.0.0.1}"
NANOMQ_TCP_PORT="${NANOMQ_TCP_PORT:-1883}"
NANOMQ_CONF="${NANOMQ_CONF:-$INSTALL_DIR/nanomq/config/nanomq.conf}"

resolve_nanomq_bin() {
  if [ -n "${NANOMQ_BIN:-}" ] && [ -f "$NANOMQ_BIN" ]; then
    return 0
  fi
  local c
  for c in \
    "$MQTT_INFLUX_CASE_ROOT/.local/nanomq/bin/nanomq.exe" \
    "$MQTT_INFLUX_CASE_ROOT/.local/nanomq/bin/nanomq" \
    "$INSTALL_DIR/nanomq/bin/nanomq.exe" \
    "$INSTALL_DIR/nanomq/bin/nanomq"
  do
    if [ -f "$c" ]; then
      NANOMQ_BIN="$c"
      return 0
    fi
  done
  return 1
}

if ! resolve_nanomq_bin; then
  echo "未找到 nanoMQ。请先按 docs/installation/nanomq-local-installation.md 安装到 .local/nanomq，或设置 NANOMQ_BIN。"
  exit 1
fi

if [ ! -f "$NANOMQ_CONF" ]; then
  echo "未找到配置文件: $NANOMQ_CONF"
  exit 1
fi

echo "nanoMQ 监听: nmq-tcp://${NANOMQ_TCP_HOST}:${NANOMQ_TCP_PORT}"
echo "配置文件: $NANOMQ_CONF"
echo "smoke_test: MQTT_HOST=${NANOMQ_TCP_HOST} MQTT_PORT=${NANOMQ_TCP_PORT} bash scripts/test/smoke.sh"
echo "桥接服务: 确保 config.yaml 中 mqtt.broker 为 tcp://${NANOMQ_TCP_HOST}:${NANOMQ_TCP_PORT}"
echo

exec "$NANOMQ_BIN" start --conf "$NANOMQ_CONF" --url "nmq-tcp://${NANOMQ_TCP_HOST}:${NANOMQ_TCP_PORT}"