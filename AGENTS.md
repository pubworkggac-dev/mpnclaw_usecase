# MQTT-InfluxDB Bridge Service

**Generated:** 2026-05-13
**Commit:** 7cecd54
**Branch:** main

## OVERVIEW

Python service bridging IoT MQTT telemetry → InfluxDB v2 with FastAPI REST interface. Core stack: asyncio MQTT, InfluxDB v2 client, FastAPI, Pydantic v2.

## STRUCTURE

```
usecase/1.mqtt_influxdb/
├── src/
│   ├── main.py              # Entry: uvicorn/FastAPI
│   ├── config.py            # YAML + env var config
│   ├── lineprotocol.py      # InfluxDB Line Protocol encoder
│   ├── mqtt/                # MQTT subscriber + handler
│   ├── influxdb/            # Batch writer + SQL query
│   ├── api/                 # FastAPI routes + models
│   ├── models/              # Pydantic data models
│   ├── adapters/            # Protocol adapters (jiujingyun/simple/router)
│   └── ws_client.py         # WebSocket direct push client
├── scripts/
│   ├── start/               # Service launchers (bridge, influxdb, mosquitto, nanomq)
│   ├── install/              # Docker/native install scripts + docker-compose
│   ├── init/                 # InfluxDB v2 init script
│   ├── test/                 # Smoke test scripts
│   ├── test_data/            # Test data generators (simulate devices, batch, property)
│   ├── env_common.sh         # Common environment variables
│   ├── run.sh                # Main run script
│   ├── simulate_device.py     # Device simulator
│   └── mosquitto-dev.conf    # Mosquitto dev config
├── tests/                   # pytest suites
├── openclaw/                # OpenCLAW skill files
├── docs/                    # References + test cases
├── config.yaml
└── pyproject.toml
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| MQTT subscription | `src/mqtt/client.py` | asyncio-mqtt, auto-reconnect |
| Telemetry parsing | `src/mqtt/handler.py` | JSON payload → TelemetryMessage |
| Batch write to InfluxDB | `src/influxdb/writer.py` | 5000 points / 10s flush |
| SQL query InfluxDB | `src/influxdb/query.py` | Flux query builder |
| REST API routes | `src/api/routes.py` | FastAPI router |
| Data models | `src/models/telemetry.py` | Pydantic v2 models |
| Config loading | `src/config.py` | YAML + pydantic-settings |
| Protocol adapters | `src/adapters/` | jiujingyun protocol |
| WebSocket Client | `src/ws_client.py` | WebSocket direct push to Gateway |
| Start bridge | `scripts/start_bridge.sh` | `uv run python -m src.main` |

## COMMANDS

```bash
# Install
uv sync

# Run bridge
uv run python -m src.main

# Run tests
pytest tests/ -v

# Smoke test (requires broker + influxdb running)
bash scripts/run_smoke_test.sh

# Multi-terminal smoke env
bash scripts/start_influxdb_native.sh
bash scripts/init_influxdb_v2.sh
NANOMQ_TCP_PORT=1884 bash scripts/start_nanomq.sh
MQTT_BROKER=tcp://127.0.0.1:1884 bash scripts/start_bridge.sh
MQTT_HOST=127.0.0.1 MQTT_PORT=1884 bash scripts/run_smoke_test.sh
```

## KEY DECISIONS

| Decision | Rationale |
|----------|-----------|
| Batch writes (5000/10s) | ~200k points/sec throughput |
| InfluxDB v2 only | Not v1 compatible |
| MQTT auto-reconnect | Exponential backoff |
| JSON logging | Machine-parseable |
| Pydantic v2 models | FastAPI validation |
| asyncio MQTT client | Non-blocking |

## ENVIRONMENT VARS

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER` | `tcp://localhost:1883` | MQTT broker URL |
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB v2 address |
| `INFLUXDB_TOKEN` | (empty) | InfluxDB auth token |
| `INFLUXDB_DATABASE` | `iot_data` | Database name |
| `HTTP_PORT` | `8080` | HTTP port |
| `BATCH_SIZE` | `5000` | Points per batch |
| `BATCH_FLUSH_INTERVAL` | `10` | Flush interval (s) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `OPENCLAW_WS_URL` | `ws://localhost:18789` | Gateway WebSocket URL（无 path 前缀） |
| `OPENCLAW_IOT_WEBHOOK_SECRET` | (empty) | WebSocket auth token |
| `OPENCLAW_DEFAULT_SESSION_KEY` | `agent:main:main` | 默认 sessionKey，Agent 不传时使用 |

## ARCHITECTURE — Device Command Sync (WebSocket Direct Push)

当前实现使用 WebSocket 直连推送，Bridge 收到 MQTT 设备 reply 后通过 Gateway `sessions.send` API 主动推送结果到 Agent session，替代原 TaskFlow 方案。

### 数据流

```
Agent (LLM)               Bridge (port 8080)               OpenClaw Gateway
    │                          │                                │
    │ POST /api/v1/commands    │                                │
    │ product_key,device_key,  │                                │
    │ service_name,params      │                                │
    │─────────────────────────→│                                │
    │                          │  1. 生成 message_id (UUID)     │
    │                          │  2. 动态订阅 _reply topic      │
    │                          │  3. MQTT publish 到设备        │
    │                          │  4. 存储命令到 _commands_map    │
    │                          │  5. 启动超时检测 task          │
    │← { message_id, success } │                                │
    │                          │                                │
    │   [设备执行命令...]       │                                │
    │                          │  MQTT _reply 到达              │
    │                          │  on_command_reply()            │
    │                          │  1. 更新本地 _commands_map     │
    │                          │  2. 取消超时 task              │
    │                          │───────────────────────────────→│
    │                          │  WS sessions.send({            │
    │                          │    key, message: command_result│
    │                          │  })                            │
    │                          │  ← { ok, runId }               │
    │                          │                                │
    │ GET /api/v1/commands/    │                                │
    │ {message_id}/status      │                                │
    │─────────────────────────→│                                │
    │← { status, state }      │   ← 从本地 _commands_map 读取   │
```

### SessionKey 处理

Bridge 从 `config.yaml` 的 `openclaw.default_session_key` 获取默认 sessionKey，Agent 可显式传 `session_key` 覆盖：

```yaml
openclaw:
  default_session_key: "agent:main:main"
  ws_url: "ws://localhost:18789"
  webhook_secret: "..."      # 同时用于 WebSocket auth
```

- Agent 调用 `send_command` 时可传 `session_key` 参数覆盖默认值
- 命令结果通过 `sessions.send` 推送到指定 sessionKey 对应的会话
- 超时通知也通过 `sessions.send` 推送

## DESIGN NOTES

### 1. Reply 订阅不 unsubscribe

`send_command` 动态 subscribe `_reply` Topic，但**从不 unsubscribe**。这**不是 bug**，原因：

- Reply Topic 是 per-(device, service) 的：`/system/{pk}/{dk}/thing/service/{name}_reply`
- 并发发往同一 device+service 的多个命令共享同一条 Topic
- 回复在 payload.id 中区分（`{"id": "<message_id>", ...}`），不在 Topic 中
- 如果回复后立即 unsubscribe，会丢失同一 Topic 上其他并发命令的回复

MQTT Broker 处理订阅的效率极高，数百条订阅无压力。无需引用计数 unsubscribe。

### 2. 命令回复链路

```
MQTT _reply
  → MqttClient._on_message
    → _reply_queue.put()                    ← 按 topic 后缀 "_reply" 判别
      → _reply_consumer() 消费队列
        → handle_command_reply()            ← 解析 payload.id
          → asyncio.create_task(on_command_reply())
            → 更新 _commands_map → 取消超时 → WS sessions.send 推送
```

### 3. 多会话隔离

当前 sessionKey 通过 `config.yaml` 的 `default_session_key` 配置，Agent 可在调用 `send_command` 时传 `session_key` 参数覆盖。`CommandRequest` 模型已支持 `session_key` 透传。

### 4. OpenClaw 集成参考

| 文件 | 作用 |
|------|------|
| `openclaw/iot-mqtt-bridge/SKILL.md` | Agent Skill：告诉 LLM 如何调用 Bridge API |
| `openclaw/iot-mqtt-bridge/references/tools.md` | 工具参数定义（health, query, send_command） |
| `openclaw/iot-mqtt-bridge/references/agent-guidelines.md` | 命令下发指南和常用命令示例 |
| `openclaw/iot-mqtt-bridge/scripts/adapter.sh` | Shell 适配器，封装 curl 调用 Bridge API |
| `src/ws_client.py` | WebSocket 客户端：connect / reconnect / sessions.send |
