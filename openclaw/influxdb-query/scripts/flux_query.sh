#!/bin/bash
# InfluxDB Flux query adapter for influxdb-query skill.
# Uses INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_DATABASE environment variables.
set -euo pipefail

INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-}"
INFLUXDB_ORG="${INFLUXDB_ORG:-my-org}"
INFLUXDB_DATABASE="${INFLUXDB_DATABASE:-iot_data}"

CMD="${1:-help}"

require_arg() {
    local name="$1"
    local value="${2:-}"
    if [ -z "$value" ]; then
        echo "missing required arg: $name" >&2
        exit 2
    fi
}

jq_or_cat() {
    local file="$1"
    if command -v jq >/dev/null 2>&1; then
        jq .
    else
        cat "$file"
    fi
}

case "$CMD" in
    flux_query)
        flux="${2:-}"
        require_arg "flux" "$flux"
        database="${3:-$INFLUXDB_DATABASE}"

        query_url="${INFLUXDB_URL}/api/v2/query?org=${INFLUXDB_ORG}"
        payload=$(jq -n --arg f "$flux" '{query: $f, type: "flux"}')

        headers=("-H" "Content-Type: application/json" "-H" "Accept: application/csv")
        if [ -n "$INFLUXDB_TOKEN" ]; then
            headers+=("-H" "Authorization: Token ${INFLUXDB_TOKEN}")
        fi

        tmpfile=$(mktemp)
        http_code=$(curl -s -X POST "${query_url}" "${headers[@]}" -d "$payload" -o "$tmpfile" -w "%{http_code}")

        if [ "$http_code" = "200" ]; then
            # Parse CSV response and convert to JSON
            if command -v python3 >/dev/null 2>&1; then
                python3 -c "
import csv, sys, json
reader = csv.DictReader(sys.stdin)
rows = [row for row in reader if row and not row.get('result','').startswith('#')]
print(json.dumps({'success': True, 'data': rows, 'meta': {'count': len(rows)}}, ensure_ascii=False))
" < "$tmpfile" || cat "$tmpfile"
            else
                cat "$tmpfile"
            fi
        else
            echo "{\"success\": false, \"error\": \"HTTP ${http_code}\", \"data\": []}"
        fi
        rm -f "$tmpfile"
        ;;

    health)
        if [ -n "$INFLUXDB_TOKEN" ]; then
            curl -s -o /dev/null -w "%{http_code}" "${INFLUXDB_URL}/health" \
                -H "Authorization: Token ${INFLUXDB_TOKEN}" \
                -H "Content-Type: application/json" || echo "unreachable"
        else
            curl -s -o /dev/null -w "%{http_code}" "${INFLUXDB_URL}/health" || echo "unreachable"
        fi
        ;;

    list_buckets)
        if [ -z "$INFLUXDB_TOKEN" ]; then
            echo "{\"success\": false, \"error\": \"INFLUXDB_TOKEN not set\", \"data\": []}"
            exit 0
        fi
        curl -s "${INFLUXDB_URL}/api/v2/buckets" \
            -H "Authorization: Token ${INFLUXDB_TOKEN}" \
            -H "Content-Type: application/json" | jq '.buckets[]?.name' 2>/dev/null || echo "failed"
        ;;

    list_measurements)
        database="${2:-$INFLUXDB_DATABASE}"
        flux="import \"influxdata/influxdb/schema\"; schema.measurements(bucket: \"${database}\")"
        scripts/flux_query.sh flux_query "$flux" "$database"
        ;;

    help|*)
        echo "Usage: $0 <command> [args]" >&2
        echo ""
        echo "Commands:"
        echo "  flux_query '<flux>' [database]  Execute Flux query"
        echo "  health                           Check InfluxDB reachability"
        echo "  list_buckets                     List available buckets"
        echo "  list_measurements [database]      List measurements in bucket"
        exit 1
        ;;
esac