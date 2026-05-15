#!/bin/bash
# OpenClaw adapter for iot-mqtt-bridge skill.
# Uses OPENCLAW_ADAPTER_BASE_URL (default: http://localhost:8080).
set -euo pipefail

BASE_URL="${OPENCLAW_ADAPTER_BASE_URL:-http://localhost:8080}"
CMD="${1:-help}"

require_arg() {
    local name="$1"
    local value="${2:-}"
    if [ -z "$value" ]; then
        echo "missing required arg: $name" >&2
        exit 2
    fi
}

case "$CMD" in
    query_devices)
        curl -s "${BASE_URL}/api/v1/devices"
        ;;
    query_device_telemetry)
        device_id="${2:-}"
        require_arg "device_id" "$device_id"
        start="${3:--1h}"
        end="${4:-now}"
        limit="${5:-100}"
        curl -s "${BASE_URL}/api/v1/devices/${device_id}/telemetry?start=${start}&end=${end}&limit=${limit}"
        ;;
    query_device_status)
        device_id="${2:-}"
        require_arg "device_id" "$device_id"
        curl -s "${BASE_URL}/api/v1/devices/${device_id}/status"
        ;;
    query_sql)
        sql="${2:-}"
        require_arg "sql" "$sql"
        curl -s -X POST "${BASE_URL}/api/v1/query" \
            -H "Content-Type: application/json" \
            -d "{\"sql\": \"${sql}\"}"
        ;;
    health)
        curl -s "${BASE_URL}/health"
        ;;
    send_command)
        product_key="${2:-}"
        device_key="${3:-}"
        service_name="${4:-}"
        params_json="${5:-{}}"
        session_key="${6:-}"
        require_arg "product_key" "$product_key"
        require_arg "device_key" "$device_key"
        require_arg "service_name" "$service_name"
        if [ -n "$session_key" ]; then
            curl -s -X POST "${BASE_URL}/api/v1/commands" \
                -H "Content-Type: application/json" \
                -d "{\"product_key\": \"${product_key}\", \"device_key\": \"${device_key}\", \"service_name\": \"${service_name}\", \"params\": ${params_json}, \"session_key\": \"${session_key}\"}"
        else
            curl -s -X POST "${BASE_URL}/api/v1/commands" \
                -H "Content-Type: application/json" \
                -d "{\"product_key\": \"${product_key}\", \"device_key\": \"${device_key}\", \"service_name\": \"${service_name}\", \"params\": ${params_json}}"
        fi
        ;;  
    send_command_sync)
        product_key="${2:-}"
        device_key="${3:-}"
        service_name="${4:-}"
        params="${5:-{}}"
        session_key="${6:-}"
        require_arg "product_key" "$product_key"
        require_arg "device_key" "$device_key"
        require_arg "service_name" "$service_name"
        if [ -n "$session_key" ]; then
            curl -s -X POST "${BASE_URL}/api/v1/commands" \
                -H "Content-Type: application/json" \
                -d "{\"product_key\":\"$product_key\",\"device_key\":\"$device_key\",\"service_name\":\"$service_name\",\"params\":$params,\"session_key\":\"$session_key\"}"
        else
            curl -s -X POST "${BASE_URL}/api/v1/commands" \
                -H "Content-Type: application/json" \
                -d "{\"product_key\":\"$product_key\",\"device_key\":\"$device_key\",\"service_name\":\"$service_name\",\"params\":$params}"
        fi
        ;;  
    send_command_sync)
        product_key="${2:-}"
        device_key="${3:-}"
        service_name="${4:-}"
        params="${5:-{}}"
        require_arg "product_key" "$product_key"
        require_arg "device_key" "$device_key"
        require_arg "service_name" "$service_name"
        curl -s -X POST "${BASE_URL}/api/v1/commands" \
            -H "Content-Type: application/json" \
            -d "{\"product_key\":\"$product_key\",\"device_key\":\"$device_key\",\"service_name\":\"$service_name\",\"params\":$params}"
        ;;
    get_command_status)
        message_id="${2:-}"
        require_arg "message_id" "$message_id"
        curl -s "${BASE_URL}/api/v1/commands/${message_id}/status"
        ;;
    help|*)
        echo "Usage: $0 <command> [args]" >&2
        echo ""
        echo "Commands:"
        echo "  query_devices                       List all devices"
        echo "  query_device_telemetry <id> [start] [end] [limit]  Device telemetry"
        echo "  query_device_status <id>             Latest device status"
        echo "  query_sql '<query>'                  SQL compatibility endpoint (v2 returns not available)"
        echo "  health                              Health check"
        echo "  send_command <pk> <dk> <service> [params_json] [session_key]  Send device command (async)"
        echo "  send_command_sync <pk> <dk> <service> [params] [session_key]  Send device command (sync)"
        echo "  get_command_status <message_id>      Query command execution status"
        exit 1
        ;;
esac