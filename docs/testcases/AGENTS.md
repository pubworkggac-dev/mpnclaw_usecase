# Testcases 目录知识库

**Generated:** 2026-05-15
**目标:** `usecase/1.mqtt_influxdb` 测试用例集

---

## OVERVIEW
本目录的目标是作为对外交付的文档，需要能实现几个效果 
1. 可以给别人讲清楚这个用例是怎么实现的
2. 定义了哪些测试验证的案例场景
3. 怎么进行这些案例的实际验证

本目录存放 `usecase/1.mqtt_influxdb` 的完整测试用例文档，覆盖 MQTT-InfluxDB Bridge Service 的冒烟、能力、运维操作、生命周期、物模型、对抗和端到端测试。

**验证对象:** MQTT → InfluxDB v2 桥接 + REST API + 九井云设备运维
**执行方式:** OpenClaw Agent 通过 HTTP API / MQTT 协议与服务交互

---

## STRUCTURE

```
testcases/
├── testcases.md                      # 测试用例全集（35 个用例，含 7 个 E2E）
├── jiujing-protocol-test-design.md    # 九井云协议测试设计（白盒约束建模）
└── implementation_flow.md             # MQTT-InfluxDB Bridge 实现架构与流程
```

---

## WHERE TO LOOK

| 任务 | 文档 | 说明 |
|------|------|------|
| 快速执行测试 | `testcases.md` §0 | OpenClaw Agent CLI 执行方法、环境准备 |
| 冒烟测试 | `testcases.md` §3 | TC-SMOKE-001~003，核心链路可用性 |
| 九井云协议层测试设计 | `jiujing-protocol-test-design.md` | B1~B7 业务约束、错误模型、TC-REPLY/OTA/PROFILE-* |
| OTA/配置/文件获取多轮交互 | `testcases.md` §6 | TC-LIFE-001~005，生命周期层 |
| 命令下发→回复闭环 | `testcases.md` §4 | TC-OPS-001~008，运维操作层 |
| 端到端数据流验证 | `testcases.md` §13 | E2E-001~004，含 E2E-003/E2E-004 需设备模拟 |
| 协议实现架构 | `implementation_flow.md` | Bridge Service 组件协作、Topic 格式、命令同步流程 |

---

## CONVENTIONS

### 测试用例分类体系

| 层级 | 前缀 | 用例数 | 执行时机 |
|------|------|--------|----------|
| 冒烟层 | TC-SMOKE-* | 3 | 每次 CI / 服务启动 |
| 能力层 | TC-CAP-* | 8 | 每次 PR / 定期 |
| 运维操作层 | TC-OPS-* | 8 | 每次 PR / 定期 |
| 生命周期层 | TC-LIFE-* | 5 | 定期 / 发布前 |
| 物模型层 | TC-MODEL-* | 3 | 每次 PR / 定期 |
| 对抗层 | TC-ADV-* | 8 | 定期 / 发布前 |
| 端到端 | E2E-* | 4 | 定期 / 发布前 |
| **总计** | | **35+4** | |

### 九井云协议测试 TC ID 体系（白盒协议层）

| 前缀 | 范围 | 来源文档 |
|------|------|----------|
| TC-REPLY-001~006 | Command reply 解析 | `jiujing-protocol-test-design.md` §5 |
| TC-OTA-001~004 | OTA upgrade/process 解析 | `jiujing-protocol-test-design.md` §5 |
| TC-PROFILE-001~003 | Profile download/process 解析 | `jiujing-protocol-test-design.md` §5 |

### 测试数据格式约定

- 所有测试数据必须贴合九井云真实协议格式
- HTTP 客户端调用 REST API 验证响应
- MQTT 客户端发布/订阅含九井云协议格式的消息
- 数据校验解析 JSON / Line Protocol 验证正确性

---

## COMMANDS

### 环境准备

```bash
cd /path/to/openclaw
export OPENCLAW_STATE_DIR="$(pwd)/workspaces/mpnclaw"
export OPENCLAW_CONFIG_PATH="$(pwd)/workspaces/mpnclaw/openclaw.json"
openclaw agents list
```

### 服务依赖启动

```bash
# InfluxDB v2
bash scripts/start_influxdb_native.sh

# MQTT Broker
bash scripts/start_nanomq.sh  # 或 start_mosquitto.sh

# Bridge Service
bash scripts/start_bridge.sh
```

### 冒烟测试

```bash
# 九井云格式（默认）
TEST_MODE=jiujingyun bash smoke.sh

# 简单格式
TEST_MODE=simple bash smoke.sh
```

### 通过 OpenClaw Agent 执行测试

```bash
# 方式 A：直接发送消息
openclaw agent --agent ueg-superclaw --message "使用 adapter.sh 查询设备列表" --timeout 60

# 方式 B：通过 adapter.sh 验证 Bridge API
export OPENCLAW_ADAPTER_BASE_URL=http://localhost:8080
bash openclaw/iot-mqtt-bridge/scripts/adapter.sh health
bash openclaw/iot-mqtt-bridge/scripts/adapter.sh query_devices
bash openclaw/iot-mqtt-bridge/scripts/adapter.sh query_device_status <device_id>
```

### 生命周期测试（OTA/配置/文件获取）

需要 Agent 订阅相关 reply/process 主题，通过 HTTP API 下发命令，模拟设备按协议流程发布各阶段回复。参考 `testcases.md` §6 和 `implementation_flow.md` §1.3 的五类通信交互模式。

---

## KEY METRICS

| 指标 | 值 |
|------|-----|
| 九井云协议解析约束数 | B1~B7（7 条） |
| 错误模型数 | 6 种 |
| 九井云协议层 TC 数 | 13 个（TC-REPLY/OTA/PROFILE-*） |
| 端到端用例数 | 4 个（E2E-001~004） |
| 需要设备模拟的用例 | E2E-003（命令下发→回复）、E2E-004（OTA 3步交互） |

---

## REFERENCE

- 九井云协议文档: `usecase/1.mqtt_influxdb/docs/reference/`
  - `2.jiujing_mqtt连接.md` — MQTT 连接与五类通信方式
  - `3.jiujing_物模型属性定义及上报.md` — 属性格式与 Topic
  - `4.jiujing_设备功能.md` — 服务命令与回复格式
  - `5.jiujing_ota升级.md` — OTA 升级三步交互
  - `6.jiujing_获取设备配置文件或日志文件.md` — 文件获取
- Bridge Service 实现: `usecase/1.mqtt_influxdb/openclaw/iot-mqtt-bridge/`