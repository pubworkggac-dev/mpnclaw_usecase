# MQTT-InfluxDB Bridge Service

> IoT device telemetry collector: MQTT → InfluxDB → HTTP API

A Python service that subscribes to MQTT topics from IoT devices, batches telemetry messages, and writes them to InfluxDB. Provides a REST API for querying device data.

## 文档与脚本

- 本用例内：
  - [nanoMQ 本地安装与验证](docs/installation/nanomq-local-installation.md)
  - [多终端冒烟环境（启动顺序、端口对齐）](scripts/README.md)
- 外部依赖安装说明若存在于仓库其它模块，请以对应路径为准（本目录当前仅收录 nanoMQ 安装文档）。

## Architecture

```
IoT Devices ──MQTT──► MQTT Broker (Mosquitto / nanoMQ) ──► Bridge Service ──► InfluxDB v2
                                              │
                                              ▼
                                          FastAPI (REST API)
                                              │
                                              ▼
                                         OpenCLAW Agent
```

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- MQTT broker（支持 Mosquitto / nanoMQ，或其他兼容 MQTT 的 broker）
- InfluxDB OSS v2（`influxd`，默认端口 `8086`）

### 本地冒烟环境（多终端）

在各自终端前台运行组件后，再执行一次性冒烟脚本，详见 **`scripts/README.md`**。常用入口：

| 脚本 | 说明 |
|------|------|
| `scripts/start/influxdb.sh` | 本机 InfluxDB v2（`influxd`） |
| `scripts/start/influxdb_docker.sh` | Docker 跑 InfluxDB v2（可选） |
| `scripts/start/nanomq.sh` | nanoMQ |
| `scripts/start/mosquitto.sh` | Mosquitto（与 nanoMQ 二选一） |
| `scripts/start/bridge.sh` | 桥接服务（`uv sync` + `uv run python -m src.main`） |
| `scripts/test/smoke.sh` | 端到端冒烟测试 |

### Installation

```bash
# Clone and enter directory
cd usecase/1.mqtt_influxdb

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Configuration

Edit `config.yaml` or use environment variables:

```bash
# Option 1: Edit config.yaml
vim config.yaml

# Option 2: Environment variables
export MQTT_BROKER=tcp://localhost:1883
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=your-token-here
export HTTP_PORT=8080
```

> 说明：本项目统一使用 InfluxDB OSS v2，默认地址 `http://localhost:8086`。

### Run the Service

```bash
uv run python -m src.main
```

或使用已激活的 `.venv`：`python -m src.main`。

## API Reference

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "mqtt_connected": true,
  "influxdb_connected": true
}
```

### List Devices

```bash
curl http://localhost:8080/api/v1/devices
```

### Device Telemetry

```bash
# Last hour of data
curl "http://localhost:8080/api/v1/devices/sensor-001/telemetry"

# Custom time range
curl "http://localhost:8080/api/v1/devices/sensor-001/telemetry?start=-24h&limit=1000"
```

### Device Status

```bash
curl http://localhost:8080/api/v1/devices/sensor-001/status
```

### Raw SQL Query

```bash
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT device_id, AVG(value) as avg FROM device_telemetry WHERE time >= NOW() - INTERVAL '\''1 hour'\'' GROUP BY device_id"}'
```

## Sending Test Data

### Via MQTT

下面示例使用 `mosquitto_pub`，如果你使用 nanoMQ 作为 broker，也可使用任意 MQTT publish 客户端发送到同样的 topic/payload：

```bash
mosquitto_pub -t devices/test-sensor/telemetry \
  -m '{"device_id": "test-sensor", "sensor_type": "temperature", "value": 22.5, "unit": "celsius"}'
```

### Via Python

```bash
python -c "
from src.models.telemetry import TelemetryMessage
from src.influxdb.writer import InfluxDBWriter
from src.config import load_config
writer = InfluxDBWriter(load_config())
writer.start()
writer.write(TelemetryMessage(device_id='demo', sensor_type='temp', value=25.0))
writer.stop()
"
```

## Smoke Test

依赖 Broker、InfluxDB、桥接均已启动（顺序见 `scripts/README.md`）：

```bash
bash scripts/test/smoke.sh
```

若 MQTT 监听非默认 `1883`，请设置 `MQTT_HOST` / `MQTT_PORT` 与 Broker 一致。

## OpenCLAW Integration

The service includes OpenCLAW skill files for agent integration:

```bash
# From the openclaw/ directory
./scripts/adapter.sh query_devices
./scripts/adapter.sh query_device_telemetry sensor-001
./scripts/adapter.sh query_sql "SELECT COUNT(*) FROM device_telemetry"
```

## Project Structure

```
1.mqtt_influxdb/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration
│   ├── lineprotocol.py      # InfluxDB Line Protocol
│   ├── mqtt/
│   │   ├── client.py        # MQTT client
│   │   └── handler.py       # Message handler
│   ├── influxdb/
│   │   ├── writer.py         # Batch writer
│   │   └── query.py          # SQL query
│   ├── api/
│   │   ├── routes.py        # FastAPI routes
│   │   └── models.py        # API models
│   └── models/
│       └── telemetry.py     # Data models
├── docs/
│   └── installation/
│       └── nanomq-local-installation.md
├── openclaw/
│   ├── SKILL.md             # OpenCLAW skill
│   ├── TOOLS.md             # Tool definitions
│   ├── AGENTS.md            # Agent guidelines
│   └── scripts/
│       ├── adapter.sh       # Shell adapter
│       └── query_devices.py # Python adapter
├── scripts/
│   ├── README.md            # 多终端启动顺序说明
│   ├── env_common.sh        # 脚本共用路径
│   ├── run.sh              # 主运行脚本
│   ├── simulate_device.py   # 模拟设备发数
│   ├── mosquitto-dev.conf
│   ├── init/               # 初始化脚本
│   │   └── influxdb_v2.sh
│   ├── install/            # 安装脚本
│   ├── start/              # 启动脚本
│   │   ├── bridge.sh
│   │   ├── influxdb.sh
│   │   ├── influxdb_docker.sh
│   │   ├── mosquitto.sh
│   │   └── nanomq.sh
│   └── test/               # 测试脚本
│       ├── smoke.sh        # 端到端冒烟
│       └── jiujingyun_smoke_test.sh
├── config.yaml              # Configuration
├── pyproject.toml           # Dependencies
└── README.md                # This file
```

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Add New Dependencies

```bash
uv add <package-name>
```

### Run with Debug Logging

```bash
export LOG_LEVEL=DEBUG
python -m src.main
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Batch writes (5000/10s) | Optimized for ~200k points/sec throughput |
| Mock InfluxDB mode | Development without real InfluxDB instance |
| Background MQTT thread | Non-blocking message reception |
| Exponential backoff reconnection | Robust against broker restarts |
| Pydantic v2 models | Automatic FastAPI validation + serialization |
| JSON logging | Machine-parseable logs |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER` | `tcp://localhost:1883` | MQTT broker URL（可指向 Mosquitto / nanoMQ） |
| `INFLUXDB_URL` | `http://localhost:8086`（与 `config.yaml` 一致） | InfluxDB v2 地址 |
| `INFLUXDB_TOKEN` | (empty) | InfluxDB auth token |
| `INFLUXDB_DATABASE` | `iot_data` | InfluxDB database name |
| `HTTP_HOST` | `0.0.0.0` | HTTP bind address |
| `HTTP_PORT` | `8080` | HTTP port |
| `BATCH_SIZE` | `5000` | Points per batch |
| `BATCH_FLUSH_INTERVAL` | `10` | Flush interval (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |


##  Quick Test 

```bash
cd usecase/1.mqtt_influxdb
bash scripts/start/influxdb.sh
bash scripts/init/influxdb_v2.sh
NANOMQ_TCP_PORT=1884 bash scripts/start/nanomq.sh
MQTT_BROKER=tcp://127.0.0.1:1884 bash scripts/start/bridge.sh
MQTT_HOST=127.0.0.1 MQTT_PORT=1884 bash scripts/test/smoke.sh
OPENCLAW_ADAPTER_BASE_URL=http://localhost:8080 bash openclaw/scripts/adapter.sh query_devices
```