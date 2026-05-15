# MQTT Module

**Parent:** `AGENTS.md`

## OVERVIEW

MQTT subscriber with asyncio-mqtt, auto-reconnect with exponential backoff, JSON payload parsing.

## STRUCTURE

```
mqtt/
├── __init__.py
├── client.py    # asyncio MQTT subscriber
└── handler.py   # TelemetryMessage parsing
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| MQTT connect/subscribe | `client.py` | `connect_mqtt()`, topic `devices/+/telemetry` |
| Auto-reconnect | `client.py` | Exponential backoff, `asyncio.sleep()` retry |
| Message parsing | `handler.py` | JSON → `TelemetryMessage` Pydantic model |
| Reconnect config | `client.py` | `MQTT_RECONNECT_INTERVAL_MAX=60s` |

## CONVENTIONS

- Topic pattern: `devices/{device_id}/telemetry`
- Payload: `{"device_id", "sensor_type", "value", "unit", "timestamp?"}`
- Uses `asyncio-mqtt` (not paho) for non-blocking I/O
