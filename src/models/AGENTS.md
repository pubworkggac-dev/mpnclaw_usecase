# Models Module

**Parent:** `AGENTS.md`

## OVERVIEW

Pydantic v2 data models for MQTT payloads and InfluxDB data.

## STRUCTURE

```
models/
├── __init__.py
├── telemetry.py   # TelemetryMessage
└── command.py     # Command model (if used)
```

## WHERE TO LOOK

| Model | File | Fields |
|-------|------|--------|
| `TelemetryMessage` | `telemetry.py` | `device_id`, `sensor_type`, `value`, `unit`, `timestamp` |
| `Command` | `command.py` | Device command model |

## CONVENTIONS

- Uses Pydantic v2 with `model_config`
- `timestamp` field is optional, defaults to current time if missing
