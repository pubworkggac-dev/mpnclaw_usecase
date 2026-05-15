# MQTT-InfluxDB Bridge 测试用例集

**版本:** v1.0
**日期:** 2026-05-15
**验证对象:** `usecase/1.mqtt_influxdb` 服务（MQTT → InfluxDB v2 桥接 + REST API + 九井云设备运维）

> 本目录是 `usecase/1.mqtt_influxdb` 的对外交付文档集，可向外部合作方演示或交接。

---

## 一、这个用例做了什么

**一句话说明：** 将九井云 IoT 设备（CPE Gateway）的 MQTT 数据上报桥接到 InfluxDB 时序数据库，同时支持通过 REST API 和 Agent 下发设备命令并接收回复。

**系统架构：**

```
九井云 CPE 设备
    │ MQTT (:1883)
    ▼
MQTT Broker (nanoMQ/Mosquitto)
    │ MQTT subscribe
    ▼
Bridge Service (FastAPI :6601)     ← 核心组件
    │ batch write (5000条/10s)
    ▼
InfluxDB v2 (:8086, bucket: iot_data)
    │
    │ HTTP GET /api/v1/...
    ▼
OpenClaw Agent (LLM + Gateway)
    ├── 通过 adapter.sh 查询设备/遥测
    ├── 下发命令到 Bridge → CPE
    └── 通过 WebSocket 接收命令回复
```

**五大通信模式：**

| 模式 | 方向 | Topic 示例 | 说明 |
|------|------|------------|------|
| 属性上报 | CPE → 平台 | `/system/{pk}/{dk}/thing/property/post` | 设备周期上报状态/遥测 |
| 设备功能 | 平台 → CPE → 回复 | `/system/{pk}/{dk}/thing/service/{svc}` | 下发命令，设备回复 `{id: message_id, code, data}` |
| OTA 升级 | 平台 → CPE → 确认 → 进度 | `ota/upgrade` → `ota/get/reply` → `ota/upgrade/process` | 三步交互，step 0→100 |
| 配置更新 | 平台 → CPE → 确认 → 进度 | `profile/upgrade` → `get/reply` → `upgrade/process` | 同 OTA 三步 |
| 获取文件 | 平台 → CPE → 回传 | `profile/download` → `download/process` | 两步，返回 download_url |

**关键设计点：**
- reply topic 采用**动态订阅**：下发命令时订阅 `_reply`，回复在 payload `id` 字段中区分（不退订，支持并发）
- 数据写入 InfluxDB 采用**批处理**：5000 条或 10 秒 flush 一次
- 命令回复通过 **WebSocket 直推 Agent session**：不依赖轮询

---

## 二、测试覆盖了哪些场景

### 2.1 测试分层概览

共 **35 个测试用例**，分为 7 层：

| 层级 | 覆盖目标 | 用例数 |
|------|----------|--------|
| 冒烟层 | 核心链路可用性（服务健康、设备列表、遥测查询） | 3 |
| 能力层 | 各维度主能力（设备详情、属性筛选、历史查询等） | 8 |
| 运维操作层 | 设备功能下发→回复闭环（重启、恢复出厂、VLAN 配置等） | 8 |
| 生命周期层 | OTA 升级、配置更新、文件获取多轮交互 | 5 |
| 物模型层 | 九井云属性上报格式兼容 | 3 |
| 对抗层 | 边界、异常、高并发 | 8 |
| 端到端 | 全链路数据流验证 | 4 |
| **合计** | | **35** |

### 2.2 关键场景举例

#### 场景 A：九井云属性上报 → InfluxDB 存储 → API 查询还原

1. 设备通过 MQTT 发布九井云格式属性到 `/system/{pk}/{dk}/thing/property/post`
2. Bridge 解析嵌套 params，写入 InfluxDB（batch 5000 条/10s）
3. Agent 通过 `adapter.sh query_device_telemetry` 查询
4. 验证返回数据包含九井云格式字段（DeviceID、CPU、UseMemory、MobileNetwork1.RSRP 等）

#### 场景 B：设备功能下发 → 命令回复闭环

1. Agent 订阅 reply topic `/system/{pk}/{dk}/thing/service/SetDeviceName_reply`
2. Agent 通过 `adapter.sh send_command` 下发 `SetDeviceName '{"DeviceName":"TestRouter"}'`
3. Bridge 先订阅 reply topic，再发布命令到 CPE
4. CPE 处理后发布回复 `{code:200, data:{Code:"0"}, id:<下发id>}`
5. Bridge 匹配 `id` 与 `message_id`，通过 WebSocket 推送结果到 Agent session

#### 场景 C：OTA 升级三步交互

1. Agent 下发 `ota/upgrade`（version/url/sign/pkg_name/detail_id）
2. Agent 订阅 `ota/get/reply`，验证 `detail_id` 匹配
3. CPE 发布确认到 `ota/get/reply`
4. CPE 持续上报 `ota/upgrade/process`，step 从 0 递增到 100
5. 最终 `step=100` 且 `fail` 为空表示升级成功

### 2.3 九井云协议层测试设计（白盒约束）

协议解析正确性通过以下 7 条业务约束验证：

| 约束ID | 业务规则 | 违反后的影响 |
|--------|----------|-------------|
| B1 | Command reply 的 `id` 必须与下发的 `message_id` 一致 | Bridge 无法匹配回复，命令永远 pending |
| B2 | Command reply 的 `code` 必须为 200 才表示协议层成功 | Agent 误判命令已成功 |
| B3 | Command reply 的 `data.Code` 为 "0" 才表示设备执行成功 | 设备执行失败被忽略 |
| B4 | OTA upgrade/process 的 `detail_id` 在各轮交互中保持一致 | OTA 升级状态分裂 |
| B5 | OTA upgrade/process 的 `step` 必须单调递增（0→100） | 升级状态机异常 |
| B6 | Profile download 的 `download_url` 非空且 `fail` 为空才表示成功 | 配置文件获取结果被误判 |
| B7 | 所有消息的 `method` 字段必须被正确识别 | 消息被静默丢弃 |

对应的 13 个协议层 TC（TC-REPLY-*/TC-OTA-*/TC-PROFILE-*）见 [`jiujing-protocol-test-design.md`](./jiujing-protocol-test-design.md)。

---

## 三、如何执行这些测试

### 3.1 环境准备

#### Linux / macOS

**前提条件：** Docker 已安装

```bash
# 1. 克隆仓库后初始化
cd /path/to/my-openclaw
bash scripts/link-ai-coding-spec.sh --force

# 2. 设置环境变量
export OPENCLAW_STATE_DIR="$(pwd)/workspaces/mpnclaw"
export OPENCLAW_CONFIG_PATH="$(pwd)/workspaces/mpnclaw/openclaw.json"

# 3. 启动所有依赖服务（InfluxDB、MQTT Broker、Bridge Service）
cd usecase/1.mqtt_influxdb
bash scripts/start/influxdb_docker.sh &   # 或 influxdb.sh（本机）
bash scripts/start/nanomq.sh &             # 或 mosquitto.sh
bash scripts/start/bridge.sh &

# 4. 验证服务就绪
curl -s http://localhost:8080/health
```

#### Windows（PowerShell / Git Bash / WSL2）

**前提条件：** Docker Desktop for Windows 已安装并运行

```powershell
# 方式 A：直接用 bash（Git Bash / WSL2）
cd D:\coding\my_claw\my-openclaw
bash scripts/link-ai-coding-spec.sh --force

# 设置环境变量（在 bash 中）
export OPENCLAW_STATE_DIR="$(pwd)/workspaces/mpnclaw"
export OPENCLAW_CONFIG_PATH="$(pwd)/workspaces/mpnclaw/openclaw.json"

# 启动服务（注意 Windows 下后台任务语法不同）
cd usecase/1.mqtt_influxdb
bash scripts/start/influxdb_docker.sh
bash scripts/start/nanomq.sh
bash scripts/start/bridge.sh

# 验证服务就绪
curl -s http://localhost:6601/health
```

**启动设备模拟器（关键！）**

> E2E-003~006 等测试用例依赖 CPE 设备模拟器。模拟器需**单独启动**，它会：
> 1. 连接 MQTT Broker（默认 `localhost:1883`）
> 2. 订阅服务命令主题（`/system/{pk}/{dk}/thing/service/+`）
> 3. **周期性上报物模型属性**到 `/system/{pk}/{dk}/thing/property/post`（默认 30 秒一次）
> 4. 收到服务命令后自动回复 `_reply` 主题

```bash
# 在后台启动设备模拟器（使用九井云协议）
cd usecase/1.mqtt_influxdb
python scripts/simulate_device.py \
    --product-key test-product \
    --device-key cpe-sn-001 \
    --broker tcp://localhost:1883 \
    --interval 30

# 也可用 simulate_device_stream.py 持续发送（每次间隔可自定义）
python scripts/test_data/simulate_device_stream.py \
    --product-key test-product \
    --device-key cpe-sn-001 \
    --interval 5
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--product-key` | `test-product` | 九井云产品 Key |
| `--device-key` | `test-device-001` | 设备唯一标识（用 `cpe-sn-001` 匹配 API 查询） |
| `--broker` | `tcp://localhost:1883` | MQTT Broker 地址 |
| `--interval` | `30` | 属性上报间隔（秒），协议推荐 30 秒 |

```powershell
# 方式 B：使用 Docker Compose 一键启动（推荐）
cd D:\coding\my_claw\my-openclaw\usecase\1.mqtt_influxdb
docker compose -f scripts/install/docker-compose.nanomq.yml up -d

# 验证容器运行
docker ps --filter "name=nanomq" --filter "name=influxdb" --filter "name=bridge"
```

```powershell
# 方式 C：纯 Docker 手动启动
# 1. 启动 InfluxDB
docker run -d --name influxdb `
  -p 8086:8086 `
  -v influxdb-data:/var/lib/influxdb2 `
  influxdb:latest

# 2. 启动 nanoMQ
docker run -d --name nanomq `
  -p 1883:1883 -p 8083:8083 -p 8883:8883 `
  emqx/nanomq:latest

# 3. 启动 Bridge Service（需要先构建镜像或使用已有镜像）
docker run -d --name bridge `
  -p 6601:6601 `
  -e MQTT_HOST=host.docker.internal `
  -e INFLUXDB_HOST=host.docker.internal `
  --network=host `
  iot-mqtt-bridge:latest

# 4. 验证
curl http://localhost:8080/health
```

**Windows 注意事项：**

| 问题 | 解决方案 |
|------|----------|
| bash 脚本找不到 | 使用 Git Bash 或 WSL2，而非 PowerShell 原生 |
| Docker 网络访问宿主机 | 使用 `host.docker.internal` 代替 `localhost` |
| 端口冲突（1883/8086/6601） | 检查宿主机是否有其他服务占用，提前 `netstat -ano \| findstr :1883` |
| WSL2 中 Docker 访问 | 确保 Docker Desktop WSL2 integration 已开启 |
| 启动脚本报错 `Permission denied` | 在 Git Bash 中 `chmod +x scripts/start/*.sh`，或在 WSL2 中运行 |

### 3.2 冒烟测试（3 分钟完成）

**目的：** 验证核心链路可用性，每次部署后必跑

**前提：** 设备模拟器必须已启动（见 3.1 节）。等待首次 property/post 上报（约 30 秒）后再执行测试，确保 InfluxDB 中有数据。

```bash
cd usecase/1.mqtt_influxdb

# 九井云格式（默认）
TEST_MODE=jiujingyun bash scripts/test/smoke.sh

# 简单格式
TEST_MODE=simple bash smoke.sh
```

验证三个核心接口：
- `GET /health` → `status=healthy`
- `GET /api/v1/devices` → `success=true`
- `GET /api/v1/devices/{id}/telemetry` → 数据非空

### 3.3 通过 OpenClaw Agent 执行测试用例

> 以下测试模拟**真实企业用户**与 Agent 的自然语言交互。Agent 理解用户意图后，通过 Bridge API 与设备/数据库交互，返回用户友好的回答。
>
> **前提：** Gateway 已启动（`./scripts/gateway.sh -w mpnclaw`）

| 场景 | 用户说的话（测试输入） | 期望回答（验证点） |
|------|----------------------|-------------------|
| TC-SMOKE-002 | "现在有哪些设备在线？" | 返回设备列表，包含 cpe-sn-001、sensor-001 等测试设备 |
| TC-SMOKE-003 | "sensor-001 最近上报了什么数据？" | 返回 sensor-001 的最新遥测（温度、湿度等字段） |
| TC-CAP-001 | "cpe-sn-001 的最新状态是什么？" | 返回设备详情，包含 DeviceID、CPU、UseMemory 等九井云字段 |
| TC-OPS-002 | "重启 cpe-sn-001" | 设备重启成功，回复 code=200 |
| TC-OPS-008 | "给 cpe-sn-001 配置 VLAN，VLAN ID=100，Port0 和 CPU 设为 tagged 模式" | 配置下发成功，回复 code=200 且 data.Code=0 |

**执行方式：**

```bash
# 启动 Gateway（如未运行）
./scripts/gateway.sh -w mpnclaw

# 冒烟查询
openclaw agent --agent ueg-superclaw --message "现在有哪些设备在线？" --timeout 60
openclaw agent --agent ueg-superclaw --message "sensor-001 最近上报了什么数据？" --timeout 60

# 设备运维
openclaw agent --agent ueg-superclaw --message "重启 cpe-sn-001" --timeout 90
openclaw agent --agent ueg-superclaw --message "给 cpe-sn-001 配置 VLAN，VLAN ID=100，Port0 和 CPU 设为 tagged 模式" --timeout 90
```

### 3.4 生命周期测试（OTA / 配置 / 文件获取）

> 模拟企业用户在 OpenClaw Agent 上发起 OTA 升级、配置更新、设备文件获取等多轮交互场景。

| 场景 | 用户说的话 | 多轮交互说明 |
|------|----------|-------------|
| TC-LIFE-001 | "对 cpe-sn-001 执行 OTA 升级到 1.0.1" | Agent 下发升级 → 设备确认 → 进度上报（step 0→100）→ 完成 |
| TC-LIFE-002 | "OTA 升级失败了，查看 cpe-sn-001 升级结果" | 期望 step<100 且 fail 非空，服务不崩溃 |
| TC-LIFE-004 | "获取 cpe-sn-001 的配置文件" | 下发请求 → 设备返回 download_url → 验证 URL 有效 |

**示例：OTA 升级**

```bash
openclaw agent --agent ueg-superclaw \
  --message "对 cpe-sn-001 执行 OTA 升级到版本 1.0.1，升级包地址是 http://example.com/firmware.bin" \
  --timeout 120
```

完整生命周期测试用例和评价指标见 [`testcases.md`](./testcases.md) §6（TC-LIFE-*）。

### 3.5 E2E 测试（需要设备模拟）

E2E-003（设备功能下发→回复）和 E2E-004（OTA 升级）需要模拟设备行为：

```bash
# E2E-003：命令下发→回复闭环
# Step 1: Agent 订阅 reply topic
# Step 2: Agent 下发 SetDeviceName 命令
# Step 3: 模拟设备发布回复 {code:200, data:{Code:"0"}, id:<下发id>}
# Step 4: Agent 验证回复

# E2E-004：OTA 升级三步交互
# Step 1: Agent 下发 ota/upgrade
# Step 2: Agent 订阅 ota/get/reply 验证 detail_id
# Step 3: 模拟设备发布确认
# Step 4: Agent 订阅 ota/upgrade/process 验证 step 递增到 100
```

完整 E2E 测试步骤见 [`testcases.md`](./testcases.md) §13。

---

## 四、目录结构

```
testcases/
├── README.md                          # ← 本文件，对外交付入口
├── testcases.md                       # 测试用例全集（35 个 TC + 4 个 E2E，含完整执行脚本）
├── jiujing-protocol-test-design.md    # 九井云协议层测试设计（白盒约束 + 13 个 TC）
└── implementation_flow.md             # 技术实现架构（系统上下文 + Mermaid 时序图）
```

---

## 五、快速索引

| 你想知道 | 去哪里看 |
|----------|----------|
| 这个用例做了什么 | §一 系统架构 + 五大通信模式 |
| 测了哪些场景 | §二 测试分层概览 + 关键场景举例 |
| 怎么跑测试 | §三 环境准备 + 冒烟测试 + Agent 执行 |
| 冒烟测试的命令 | §3.2 |
| 完整 TC 列表和 evaluation_script | `testcases.md` |
| 九井云协议解析的约束和错误模型 | `jiujing-protocol-test-design.md` |
| 技术实现细节（Mermaid 图） | `implementation_flow.md` |