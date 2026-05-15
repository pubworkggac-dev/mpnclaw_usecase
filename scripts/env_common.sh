#!/usr/bin/env bash
# 供同目录下其它脚本 source；请勿单独依赖 exit code。
MQTT_INFLUX_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MQTT_INFLUX_CASE_ROOT="$(cd "$MQTT_INFLUX_SCRIPTS_DIR/.." && pwd)"

# 支持自定义安装目录（由 install/ 脚本设置）
INSTALL_DIR="${INSTALL_DIR:-$MQTT_INFLUX_CASE_ROOT/.local}"

export MQTT_INFLUX_SCRIPTS_DIR MQTT_INFLUX_CASE_ROOT INSTALL_DIR
