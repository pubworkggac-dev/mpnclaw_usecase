#!/usr/bin/env bash
# 启动 MQTT → InfluxDB 桥接服务
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env_common.sh
source "$SCRIPT_DIR/../env_common.sh"

# 支持 CLI 参数指定端口: bridge.sh <port>
if [ -n "${1:-}" ]; then
  export HTTP_PORT="$1"
fi

export CONFIG_PATH="${CONFIG_PATH:-$MQTT_INFLUX_CASE_ROOT/config.yaml}"

if [ ! -f "$CONFIG_PATH" ]; then
  echo "未找到配置: $CONFIG_PATH"
  exit 1
fi

cd "$MQTT_INFLUX_CASE_ROOT"

if [ "${SKIP_UV_SYNC:-0}" != "1" ]; then
  uv sync
fi

# Prevent websockets library from attempting SOCKS proxy (python-socks not installed)
export NO_PROXY="*"

echo "CONFIG_PATH=$CONFIG_PATH"
echo "工作目录: $MQTT_INFLUX_CASE_ROOT"
echo

exec uv run python -m src.main