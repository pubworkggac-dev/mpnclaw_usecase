# InfluxDB Module

**Parent:** `AGENTS.md`

## OVERVIEW

InfluxDB v2 batch writer and SQL query interface. Writer uses buffered batch writes (5000 points / 10s flush). Query uses Flux query language.

## STRUCTURE

```
influxdb/
├── __init__.py
├── writer.py   # Batch write with buffer
└── query.py   # Flux SQL query builder
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Batch write buffer | `writer.py` | `BufferedWriter` class, 5000 points/10s |
| Point → Line Protocol | `writer.py` | `write_point()` → InfluxDB Line Protocol |
| SQL/Flux query | `query.py` | `InfluxDBQuery.query()` → JSON results |
| Mock mode | `writer.py` | `INFLUXDB_TOKEN=mock` bypasses real DB |

## CONVENTIONS

- Uses `influxdb-client-python` v2 (not v1)
- Database: `iot_data` (from config)
- Measurement: `device_telemetry`
- Batch flush: 5000 points OR 10 seconds (whichever first)
