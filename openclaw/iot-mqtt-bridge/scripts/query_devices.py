#!/usr/bin/env python3
"""Query IoT device data from the MQTT-InfluxDB bridge service.

Usage:
    python query_devices.py --list
    python query_devices.py --telemetry sensor-001 --start -1h
    python query_devices.py --status sensor-001
    python query_devices.py --sql "SELECT * FROM device_telemetry LIMIT 10"
"""
import argparse
import json
import os
import sys
from urllib.request import urlopen, Request

BASE_URL = os.environ.get("OPENCLAW_ADAPTER_BASE_URL", "http://localhost:8080")


def fetch(path: str) -> dict:
    """GET request."""
    url = f"{BASE_URL}{path}"
    with urlopen(url) as resp:
        return json.loads(resp.read())


def post(path: str, data: dict) -> dict:
    """POST request."""
    url = f"{BASE_URL}{path}"
    req = Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(description="IoT Device Query Tool")
    parser.add_argument("--list", action="store_true", help="List all devices")
    parser.add_argument("--telemetry", type=str, help="Get telemetry for device")
    parser.add_argument("--status", type=str, help="Get status for device")
    parser.add_argument("--sql", type=str, help="Execute raw SQL")
    parser.add_argument("--start", type=str, default="-1h", help="Start time")
    parser.add_argument("--end", type=str, default="now", help="End time")
    parser.add_argument("--limit", type=int, default=100, help="Max results")

    args = parser.parse_args()

    if args.list:
        result = fetch("/api/v1/devices")
    elif args.telemetry:
        result = fetch(f"/api/v1/devices/{args.telemetry}/telemetry?start={args.start}&end={args.end}&limit={args.limit}")
    elif args.status:
        result = fetch(f"/api/v1/devices/{args.status}/status")
    elif args.sql:
        result = post("/api/v1/query", {"sql": args.sql})
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()