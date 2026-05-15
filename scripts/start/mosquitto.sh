#!/usr/bin/env bash
# 启动 Mosquitto
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env_common.sh
source "$SCRIPT_DIR/../env_common.sh"

MOSQUITTO_CONF="${MOSQUITTO_CONF:-$MQTT_INFLUX_SCRIPTS_DIR/mosquitto-dev.conf}"

resolve_mosquitto() {
  if [ -n "${MOSQUITTO_BIN:-}" ] && [ -f "$MOSQUITTO_BIN" ]; then
    return 0
  fi
  if command -v mosquitto >/dev/null 2>&1; then
    MOSQUITTO_BIN="$(command -v mosquitto)"
    return 0
  fi
  if [ -f "/c/Program Files/mosquitto/mosquitto.exe" ]; then
    MOSQUITTO_BIN="/c/Program Files/mosquitto/mosquitto.exe"
    return 0
  fi
  return 1
}

if ! resolve_mosquitto; then
  echo "未找到 mosquitto。请安装 Mosquitto 或设置 MOSQUITTO_BIN。"
  exit 1
fi

if [ ! -f "$MOSQUITTO_CONF" ]; then
  echo "未找到配置文件: $MOSQUITTO_CONF"
  exit 1
fi

echo "Mosquitto: $MOSQUITTO_BIN"
echo "配置: $MOSQUITTO_CONF"
echo "默认监听 1883；smoke_test 可使用默认 MQTT_HOST/MQTT_PORT。"
echo

exec "$MOSQUITTO_BIN" -c "$MOSQUITTO_CONF"