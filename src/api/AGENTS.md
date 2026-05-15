# API Module

**Parent:** `AGENTS.md`

## OVERVIEW

FastAPI REST interface: device listing, telemetry queries, raw SQL, health check.

## STRUCTURE

```
api/
├── __init__.py
├── routes.py   # FastAPI router
└── models.py   # Request/response Pydantic models
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| All routes | `routes.py` | `/health`, `/api/v1/devices`, `/api/v1/query` |
| Device list | `routes.py` | `GET /api/v1/devices` |
| Telemetry query | `routes.py` | `GET /api/v1/devices/{id}/telemetry?start=&limit=` |
| SQL query | `routes.py` | `POST /api/v1/query` with JSON body |
| Request models | `models.py` | `SqlQueryRequest`, `TelemetryResponse` |

## CONVENTIONS

- Base URL: `http://localhost:8080`
- API prefix: `/api/v1`
- Uses Pydantic v2 for validation
- Returns JSON with `device_id`, `sensor_type`, `value`, `unit`, `time`
