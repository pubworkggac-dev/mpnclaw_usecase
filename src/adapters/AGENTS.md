# Adapters Module

**Parent:** `AGENTS.md`

## OVERVIEW

Protocol adapters routing MQTT messages to different backends: jiujingyun (九精云), simple, or mock router.

## STRUCTURE

```
adapters/
├── __init__.py
├── base.py       # Base adapter abstract class
├── router.py     # Adapter router
├── jiujingyun.py # 九精云 protocol adapter
└── simple.py     # Simple protocol adapter
```

## WHERE TO LOOK

| Adapter | File | Protocol |
|---------|------|----------|
| Router | `router.py` | Routes to jiujingyun/simple based on topic |
| Jiujingyun | `jiujingyun.py` | 九精云 MQTT protocol |
| Simple | `simple.py` | Simple JSON protocol |

## CONVENTIONS

- All adapters inherit from `BaseAdapter` (abstract)
- Router selects adapter based on MQTT topic pattern
- Used for protocol translation between MQTT and InfluxDB
