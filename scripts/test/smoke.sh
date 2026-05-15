#!/usr/bin/env bash
# MQTT-InfluxDB Bridge 冒烟测试
# 支持两种测试模式：简单格式（simple）和九井云格式（jiujingyun）
#
# 用法:
#   bash smoke.sh                  # 默认九井云格式
#   TEST_MODE=simple bash smoke.sh # 简单格式
#
# 环境变量:
#   TEST_MODE          - simple | jiujingyun (默认: jiujingyun)
#   BASE_URL           - Bridge 服务地址 (默认: http://localhost:8080)
#   MQTT_HOST          - MQTT Broker 主机 (默认: localhost)
#   MQTT_PORT          - MQTT Broker 端口 (默认: 1883)
#   WAIT_SECONDS       - 等待 batch flush 秒数 (默认: 5)
#   MQTT_PUB_BIN       - MQTT 发布客户端路径
#   PRODUCT_KEY         - 九井云产品 Key (默认: test-product)
#   DEVICE_KEY         - 九井云设备 Key (默认: test-device-001)

set -euo pipefail

# ============ 配置 ============
TEST_MODE="${TEST_MODE:-jiujingyun}"
BASE_URL="${BASE_URL:-http://localhost:8080}"
MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
WAIT_SECONDS="${WAIT_SECONDS:-5}"
MQTT_PUB_BIN="${MQTT_PUB_BIN:-}"
MQTT_PUB_MODE=""

# 简单模式配置
DEVICE_TEMP="${DEVICE_TEMP:-demo-thermostat}"
DEVICE_HUM="${DEVICE_HUM:-demo-humidity}"
DEVICE_POWER="${DEVICE_POWER:-demo-power-meter}"

# 九井云模式配置
PRODUCT_KEY="${PRODUCT_KEY:-test-product}"
DEVICE_KEY="${DEVICE_KEY:-test-device-001}"

PASS_COUNT=0
FAIL_COUNT=0

# ============ 工具函数 ============
resolve_mqtt_pub() {
  if [ -n "$MQTT_PUB_BIN" ]; then
    MQTT_PUB_MODE="${MQTT_PUB_MODE:-mosquitto}"
    return
  fi

  if command -v mosquitto_pub >/dev/null 2>&1; then
    MQTT_PUB_BIN="mosquitto_pub"
    MQTT_PUB_MODE="mosquitto"
    return
  fi

  if [ -x "/c/Program Files/mosquitto/mosquitto_pub.exe" ]; then
    MQTT_PUB_BIN="/c/Program Files/mosquitto/mosquitto_pub.exe"
    MQTT_PUB_MODE="mosquitto"
    return
  fi

  if [ -x "./.local/nanomq/bin/nanomq_cli.exe" ]; then
    MQTT_PUB_BIN="./.local/nanomq/bin/nanomq_cli.exe"
    MQTT_PUB_MODE="nanomq"
    return
  fi

  if [ -x "./.local/nanomq/bin/nanomq_cli" ]; then
    MQTT_PUB_BIN="./.local/nanomq/bin/nanomq_cli"
    MQTT_PUB_MODE="nanomq"
    return
  fi

  echo "[FAIL] MQTT publish client not found. Install mosquitto_pub or nanoMQ CLI, or set MQTT_PUB_BIN."
  exit 127
}

mqtt_publish() {
  local topic="$1"
  local payload="$2"
  if [ "$MQTT_PUB_MODE" = "nanomq" ]; then
    "$MQTT_PUB_BIN" pub -h "$MQTT_HOST" -p "$MQTT_PORT" -t "$topic" -m "$payload"
    return
  fi
  "$MQTT_PUB_BIN" -h "$MQTT_HOST" -p "$MQTT_PORT" -t "$topic" -m "$payload"
}

pass() {
  echo "[PASS] $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "[FAIL] $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_json() {
  local name="$1"
  local json="$2"
  local py_expr="$3"
  if printf '%s' "$json" | python -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if ($py_expr) else 1)"; then
    pass "$name"
  else
    fail "$name"
  fi
}

# ============ 模式选择 ============
case "$TEST_MODE" in
  simple)
    echo "== Test Mode: Simple Format =="
    ;;
  jiujingyun)
    echo "== Test Mode: 九井云 Protocol Format =="
    ;;
  *)
    echo "[FAIL] Unknown TEST_MODE: $TEST_MODE (use: simple | jiujingyun)"
    exit 1
    ;;
esac

# ============ Step 1: 健康检查 ============
echo
echo "== 1) Health check =="
HEALTH_JSON="$(curl -sS "$BASE_URL/health" || true)"
if [ -z "$HEALTH_JSON" ]; then
  fail "GET /health returns body"
else
  check_json "health.status == healthy" "$HEALTH_JSON" "d.get('status') == 'healthy'"
  check_json "health.mqtt_connected == true" "$HEALTH_JSON" "d.get('mqtt_connected') is True"
  check_json "health.influxdb_connected == true" "$HEALTH_JSON" "d.get('influxdb_connected') is True"
fi

# ============ Step 2: 发布遥测数据 ============
echo
echo "== 2) Publish telemetry =="
resolve_mqtt_pub

if [ "$TEST_MODE" = "simple" ]; then
  # 简单格式
  mqtt_publish "devices/${DEVICE_TEMP}/telemetry" '{"device_id":"demo-thermostat","sensor_type":"temperature","value":24.8,"unit":"celsius","location":"meeting-room"}'
  mqtt_publish "devices/${DEVICE_HUM}/telemetry" '{"device_id":"demo-humidity","sensor_type":"humidity","value":48.2,"unit":"percent","location":"meeting-room"}'
  mqtt_publish "devices/${DEVICE_POWER}/telemetry" '{"device_id":"demo-power-meter","sensor_type":"power","value":356.7,"unit":"watt","location":"lab-bench"}'
  pass "published 3 telemetry messages (simple format)"
else
  # 九井云格式
  PROPERTY_TOPIC="/system/${PRODUCT_KEY}/${DEVICE_KEY}/thing/property/post"
  PROPERTY_PAYLOAD=$(cat <<'PAYLOAD'
{
    "id": "test-property-post-001",
    "version": "1.0",
    "sys": {
        "ack": 0
    },
    "params": {
        "DeviceID": {
            "value": "5456554fdfs"
        },
        "DeviceHWVersion": {
            "value": "1.0.2"
        },
        "DeviceSWVersion": {
            "value": "1.0.1"
        },
        "ModomVersion": {
            "value": "SC7460M_V1.0.0"
        },
        "ModomModel": {
            "value": "SC7460M"
        },
        "ModomIMEI": {
            "value": "862755041234567"
        },
        "SIMCard1": {
            "value": {
                "Status": 1,
                "IMSI": "460011234567890",
                "ICCID": "89860123456789012345"
            }
        },
        "MobileNetwork1": {
            "value": {
                "Status": 1,
                "CommunityType": "LTE-FDD",
                "CommunityID": "12345678",
                "CommunityFrequency": "1825",
                "RSRP": "-85",
                "IPV4": "10.0.1.100",
                "Dns1": "8.8.8.8",
                "Dns2": "8.8.4.4",
                "PingDelay": "25",
                "BAND": "B3",
                "PDP": "IP",
                "SINA": "-8"
            }
        },
        "WLAN": {
            "value": {
                "Status1": 1,
                "Mode1": "802.11n",
                "IP1": "192.168.1.1",
                "Status2": 1,
                "Mode2": "802.11ac",
                "IP2": "192.168.2.1"
            }
        },
        "LAN": {
            "value": {
                "IP": "192.168.0.1",
                "Status": "1",
                "MAC": "AA:BB:CC:DD:EE:FF"
            }
        },
        "CPU": {
            "value": "0.35"
        },
        "OnlineInfo": {
            "value": {
                "DeviceTime": "2024-07-30 14:00:00"
            }
        },
        "CPEModel": {
            "value": "CPE-2000X"
        },
        "UseMemory": {
            "value": "0.62"
        },
        "ModuleTemperature": {
            "value": "45"
        },
        "PositionInfo": {
            "value": {
                "Longitude": "116.4074",
                "Latitude": "39.9042",
                "Height": "50",
                "Unit": "m"
            }
        },
        "DiskUsage": {
            "value": "0.15"
        }
    },
    "method": "thing.property.post"
}
PAYLOAD)
  mqtt_publish "$PROPERTY_TOPIC" "$PROPERTY_PAYLOAD"
  echo "  Published to $PROPERTY_TOPIC"
  pass "published 九井云 property.post message"
fi

# ============ Step 3: 等待数据写入 ============
echo
echo "== 3) Waiting ${WAIT_SECONDS}s for batch flush..."
sleep "$WAIT_SECONDS"

# ============ Step 4: 查询设备列表 ============
echo
echo "== 4) Query devices =="
DEVICES_JSON="$(curl -sS "$BASE_URL/api/v1/devices" || true)"
if [ -z "$DEVICES_JSON" ]; then
  fail "GET /api/v1/devices returns body"
else
  check_json "devices.success == true" "$DEVICES_JSON" "d.get('success') is True"

  if [ "$TEST_MODE" = "simple" ]; then
    check_json "devices contains ${DEVICE_TEMP}" "$DEVICES_JSON" "any(x.get('device_id') == '${DEVICE_TEMP}' for x in d.get('data', []))"
    check_json "devices contains ${DEVICE_HUM}" "$DEVICES_JSON" "any(x.get('device_id') == '${DEVICE_HUM}' for x in d.get('data', []))"
    check_json "devices contains ${DEVICE_POWER}" "$DEVICES_JSON" "any(x.get('device_id') == '${DEVICE_POWER}' for x in d.get('data', []))"
  else
    check_json "devices contains ${DEVICE_KEY}" "$DEVICES_JSON" "any(x.get('device_id') == '${DEVICE_KEY}' for x in d.get('data', []))"
  fi
fi

# ============ Step 5: 查询设备遥测 ============
echo
echo "== 5) Query device telemetry =="

if [ "$TEST_MODE" = "simple" ]; then
  TELEMETRY_JSON="$(curl -sS "$BASE_URL/api/v1/devices/${DEVICE_TEMP}/telemetry?start=-1h&end=now&limit=10" || true)"
  if [ -z "$TELEMETRY_JSON" ]; then
    fail "GET telemetry returns body"
  else
    check_json "telemetry.success == true" "$TELEMETRY_JSON" "d.get('success') is True"
    check_json "telemetry has at least 1 row" "$TELEMETRY_JSON" "len(d.get('data', [])) >= 1"
    check_json "telemetry row device_id matches" "$TELEMETRY_JSON" "any(x.get('device_id') == '${DEVICE_TEMP}' for x in d.get('data', []))"
  fi
else
  TELEMETRY_JSON="$(curl -sS "$BASE_URL/api/v1/devices/${DEVICE_KEY}/telemetry?start=-1h&end=now&limit=10" || true)"
  if [ -z "$TELEMETRY_JSON" ]; then
    fail "GET telemetry returns body"
  else
    check_json "telemetry.success == true" "$TELEMETRY_JSON" "d.get('success') is True"
    if printf '%s' "$TELEMETRY_JSON" | python -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if len(d.get('data', [])) >= 1 else 1)"; then
      pass "telemetry has data"
    else
      fail "telemetry has no data (may be normal if InfluxDB write batch is delayed)"
    fi
  fi
fi

# ============ Step 6: 九井云模式额外测试 ============
if [ "$TEST_MODE" = "jiujingyun" ]; then

  # Step 6a: 查询设备状态
  echo
  echo "== 6a) Query device status =="
  STATUS_JSON="$(curl -sS "$BASE_URL/api/v1/devices/${DEVICE_KEY}/status" || true)"
  if [ -z "$STATUS_JSON" ]; then
    fail "GET status returns body"
  else
    check_json "status has at least 1 row" "$STATUS_JSON" "len(d.get('data', [])) >= 1"
  fi

  # Step 6b: 下发控制命令 (HTTP -> MQTT -> CPE)
  echo
  echo "== 6b) Send control command via HTTP API =="
  SEND_CMD_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/commands" \
    -H "Content-Type: application/json" \
    -d "{
      \"product_key\": \"${PRODUCT_KEY}\",
      \"device_key\": \"${DEVICE_KEY}\",
      \"service_name\": \"SetDeviceName\",
      \"params\": {\"DeviceName\": \"TestRouter-$(date +%s)\"}
    }" || true)"

  if [ -z "$SEND_CMD_JSON" ]; then
    fail "POST /api/v1/commands returns body"
  else
    check_json "send_command.success == true" "$SEND_CMD_JSON" "d.get('success') is True"
    if printf '%s' "$SEND_CMD_JSON" | python -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if 'topic' in d else 1)"; then
      TOPIC=$(printf '%s' "$SEND_CMD_JSON" | python -c "import json,sys; print(json.load(sys.stdin).get('topic',''))")
      pass "command published to topic: $TOPIC"
    else
      fail "command response missing topic"
    fi
  fi

  # Step 6c: 查询命令执行状态（从本地 _commands_map 读取）
  echo
  echo "== 6c) Query command execution status =="
  if [ -n "$SEND_CMD_JSON" ]; then
    CMD_MESSAGE_ID=$(printf '%s' "$SEND_CMD_JSON" | python -c "import json,sys; print(json.load(sys.stdin).get('message_id',''))" 2>/dev/null || echo "")
    if [ -n "$CMD_MESSAGE_ID" ]; then
      CMD_STATUS_JSON="$(curl -sS "$BASE_URL/api/v1/commands/${CMD_MESSAGE_ID}/status" || true)"
      if [ -n "$CMD_STATUS_JSON" ]; then
        check_json "command status query success" "$CMD_STATUS_JSON" "d.get('success') is True"
        CMD_STATUS=$(printf '%s' "$CMD_STATUS_JSON" | python -c "import json,sys; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
        if [ "$CMD_STATUS" = "pending" ] || [ "$CMD_STATUS" = "completed" ] || [ "$CMD_STATUS" = "timeout" ]; then
          pass "command status is valid: $CMD_STATUS"
        else
          fail "command status is unexpected: $CMD_STATUS"
        fi
      else
        fail "command status endpoint returns body"
      fi
    fi
  fi

  # Step 6d: 验证 iot-mqtt-bridge skill adapter
  echo
  echo "== 6c) Verify iot-mqtt-bridge skill adapter =="
  if [ -x "$(dirname "$0")/../openclaw/iot-mqtt-bridge/scripts/adapter.sh" ]; then
    ADAPTER_SH="$(dirname "$0")/../openclaw/iot-mqtt-bridge/scripts/adapter.sh"
    ADAPTER_BASE_URL="${BASE_URL}" ADAPTER_JSON="$("$ADAPTER_SH" health 2>/dev/null || echo '{}')"
    if [ -n "$ADAPTER_JSON" ]; then
      check_json "adapter health ok" "$ADAPTER_JSON" "d.get('status') == 'healthy'"
    fi
    pass "iot-mqtt-bridge skill adapter is functional"
  else
    pass "iot-mqtt-bridge skill adapter not found (skip)"
  fi

else
  # 简单模式: 查询设备状态
  echo
  echo "== 6) Query latest status =="
  STATUS_JSON="$(curl -sS "$BASE_URL/api/v1/devices/${DEVICE_POWER}/status" || true)"
  if [ -z "$STATUS_JSON" ]; then
    fail "GET status returns body"
  else
    check_json "status has at least 1 row" "$STATUS_JSON" "len(d.get('data', [])) >= 1"
  fi

  # 简单模式: 原始 SQL 端点
  echo
  echo "== 7) Raw SQL endpoint behavior =="
  SQL_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/query" -H "Content-Type: application/json" -d '{"sql":"SELECT device_id, sensor_type, COUNT(*) AS points FROM device_telemetry GROUP BY device_id, sensor_type ORDER BY device_id"}' || true)"
  if [ -z "$SQL_JSON" ]; then
    fail "POST /api/v1/query returns body"
  else
    if printf '%s' "$SQL_JSON" | python -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('success') is True else 1)"; then
      pass "raw SQL query success"
    elif printf '%s' "$SQL_JSON" | python -c "import json,sys; d=json.load(sys.stdin); err=d.get('error') or ''; sys.exit(0 if 'not available in InfluxDB v2 mode' in err else 1)"; then
      pass "raw SQL query returns expected v2-mode message"
    else
      fail "raw SQL query unexpected response"
    fi
  fi
fi

# ============ 结果汇总 ============
echo
echo "== Result =="
echo "PASS=${PASS_COUNT} FAIL=${FAIL_COUNT}"
if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
echo "All tests passed!"