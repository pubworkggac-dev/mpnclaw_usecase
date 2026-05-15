#!/usr/bin/env bash
# 初始化 InfluxDB v2（仅首次）。若已初始化则安全跳过。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env_common.sh
source "$SCRIPT_DIR/../env_common.sh"

INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
INFLUXDB_INIT_USER="${INFLUXDB_INIT_USER:-admin}"
INFLUXDB_INIT_PASS="${INFLUXDB_INIT_PASS:-admin123456}"
INFLUXDB_INIT_ORG="${INFLUXDB_INIT_ORG:-my-org}"
INFLUXDB_INIT_BUCKET="${INFLUXDB_INIT_BUCKET:-iot_data}"
INFLUXDB_INIT_TOKEN="${INFLUXDB_INIT_TOKEN:-my-super-token}"

SETUP_CHECK="$(curl -fsS "${INFLUXDB_URL}/api/v2/setup")"
ALLOWED="$(printf '%s' "$SETUP_CHECK" | python -c "import json,sys; print(str(bool(json.load(sys.stdin).get('allowed'))).lower())")"

if [ "$ALLOWED" != "true" ]; then
  echo "InfluxDB 已初始化，跳过 setup。"
  exit 0
fi

PAYLOAD="{\"username\":\"${INFLUXDB_INIT_USER}\",\"password\":\"${INFLUXDB_INIT_PASS}\",\"org\":\"${INFLUXDB_INIT_ORG}\",\"bucket\":\"${INFLUXDB_INIT_BUCKET}\",\"token\":\"${INFLUXDB_INIT_TOKEN}\"}"
curl -fsS -X POST "${INFLUXDB_URL}/api/v2/setup" -H "Content-Type: application/json" -d "$PAYLOAD" >/dev/null
echo "InfluxDB setup 完成：org=${INFLUXDB_INIT_ORG} bucket=${INFLUXDB_INIT_BUCKET}"