# MQTT-InfluxDB Bridge Service — 测试用例全集

> 本文档定义通过 **OpenClaw Agent** 自动化执行的端到端集成测试用例集。
>
> 验证对象：`usecase/1.mqtt_influxdb` 服务（MQTT → InfluxDB v2 桥接 + REST API + 九井云设备运维）
> 测试执行方式：OpenClaw Agent 通过 HTTP API / MQTT 协议与服务交互，验证行为正确性
>
> **参考文档**：所有参考链接指向 `docs/reference/` 目录下拆分后的九井云协议文档

---

## 0. OpenClaw Agent CLI 执行方法

### 0.1 环境准备

**必须先设置环境变量**，指向正确的工作空间配置：

```bash
# 1.先切换到 OpenClaw 仓库根目录,如果是以本文档为相对位置
cd ../../../../

# 设置环境变量（指向 mpnclaw 工作空间）
export OPENCLAW_STATE_DIR="$(pwd)/workspaces/mpnclaw"
export OPENCLAW_CONFIG_PATH="$(pwd)/workspaces/mpnclaw/openclaw.json"

# 验证配置
openclaw agents list
```

### 0.2 执行测试命令

```bash
# 方式 A：直接发送消息（单轮对话）
openclaw agent --agent ueg-superclaw --message "查询设备列表" --timeout 60

# 方式 B：使用 MQTT 主题发布九井云格式数据
# 先设置 MQTT 工具环境变量
export MQTT_BROKER=tcp://localhost:1883

# 方式 C：调用 adapter.sh 脚本验证 Bridge API
export OPENCLAW_ADAPTER_BASE_URL=http://localhost:8080
bash openclaw/iot-mqtt-bridge/scripts/adapter.sh query_devices
bash openclaw/iot-mqtt-bridge/scripts/adapter.sh query_device_status <device_id>
```

### 0.3 冒烟测试完整示例

```bash
cd /Users/archer/local_home/synologydrive/crossworkspace/coding/AI/agent框架/openclaw

# 1. 设置环境变量
export OPENCLAW_STATE_DIR="$(pwd)/workspaces/mpnclaw"
export OPENCLAW_CONFIG_PATH="$(pwd)/workspaces/mpnclaw/openclaw.json"

# 2. 启动 Gateway（如果尚未运行）
./scripts/gateway.sh -w mpnclaw

# 3. 验证 Bridge 服务可用
bash usecase/1.mqtt_influxdb/openclaw/iot-mqtt-bridge/scripts/adapter.sh health

# 4. 执行冒烟测试
openclaw agent --agent ueg-superclaw --message "使用 adapter.sh 查询设备列表，确认返回 success=true" --timeout 60

# 5. 执行设备状态查询
openclaw agent --agent ueg-superclaw --message "使用 adapter.sh 查询设备 cpe-sn-001 的最新状态，返回关键属性" --timeout 60
```

### 0.4 常见问题

| 问题 | 解决方案 |
|------|----------|
| `Unknown model` 错误 | 确保环境变量设置正确，Gateway 已重启 |
| `Token mismatch` 错误 | 先执行 `openclaw gateway stop && openclaw gateway start` |
| 命令无输出 | 检查 Gateway 是否运行 `openclaw gateway status` |
| 模型不可用 | 检查 `openclaw models list` 确保模型在配置中 |

---

## 1. 测试环境与前置条件

### 1.1 服务依赖

| 依赖 | 版本 | 端口 | 启动脚本 |
|------|------|------|----------|
| InfluxDB v2 | latest | 8086 | `scripts/start_influxdb_native.sh` |
| MQTT Broker (nanoMQ/Mosquitto) | latest | 1883 | `scripts/start_nanomq.sh` 或 `scripts/start_mosquitto.sh` |
| Bridge Service | 1.0.0 | 8080 | `scripts/start_bridge.sh` |

### 1.2 测试数据格式要求

所有测试数据必须贴合九井云真实协议格式，禁止使用随意构造的 mock 数据：

- **HTTP 客户端**：调用 REST API 验证响应
- **MQTT 客户端**：发布/订阅 MQTT 主题消息（含九井云协议格式）
- **数据校验**：解析 JSON / Line Protocol 验证数据正确性
- **时序控制**：等待批处理 flush 完成后查询验证；等待设备回复后验证
- **多轮交互**：设备功能下发→订阅回复→验证闭环

### 1.3 预置测试数据

测试前需通过 MQTT 注入以下设备数据：

**简单 sensor 格式（Bridge 原生格式）**：

```
Topic: devices/sensor-001/telemetry
Payload: {"device_id":"sensor-001","sensor_type":"temperature","value":25.5,"unit":"celsius","location":"room-101"}
```

**服务命令格式**（`/system/{pk}/{dk}/thing/service/{serviceName}`）：
```json
{
  "id": "命令ID",
  "version": "1.0.0",
  "params": {...},
  "method": "thing.service.SetDeviceName"
}
```

**设备回复格式**（`/system/{pk}/{dk}/thing/service/{serviceName}_reply`）：
```json
{
  "code": 200,
  "data": {"Result": "OK", "Code": "0", "Time": "1234567890"},
  "id": "对应命令ID",
  "message": "success",
  "version": "1.0"
}
```

**九井云物模型属性格式（设备运维场景）**：

```
Topic: /system/jiujing_cpe/cpe-sn-001/thing/property/post
Payload: 九井云物模型属性上报 JSON（见 [3.jiujing_物模型属性定义及上报.md]）
```

### 1.4 MQTT 通信协议约定

> 参考：[2.jiujing_mqtt连接.md](../reference/2.jiujing_mqtt连接.md)

九井云设备 MQTT 通信包含五大方式，对应不同的主题和交互模式：

| 通信方式 | 交互模式 | 主题模式 | 方向 |
|----------|----------|----------|------|
| ①属性上报 | 设备→平台 | `.../thing/property/post` | 单向 |
| ②设备功能 | 平台→设备→回复 | `.../thing/service/${serviceName}` + `_reply` | 双向 |
| ③OTA升级 | 平台→设备→确认→进度 | `.../ota/upgrade` → `get/reply` → `upgrade/process` | 3步 |
| ④配置更新 | 平台→设备→确认→进度 | `.../profile/upgrade` → `get/reply` → `upgrade/process` | 3步 |
| ⑤获取文件 | 平台→设备→回传 | `.../profile/download` → `download/process` | 2步 |

---

## 2. 用例分层总览

### 2.1 六层模型

| 层级 | 目标 | 用例数 | 执行时机 |
|------|------|--------|----------|
| **冒烟层** | 核心链路可用性 | 3 | 每次 CI / 服务启动 |
| **能力层** | 各维度主能力验证 | 8 | 每次 PR / 定期 |
| **运维操作层** | 设备功能下发→回复闭环 | 8 | 每次 PR / 定期 |
| **生命周期层** | OTA/配置/文件获取多轮交互 | 5 | 定期 / 发布前 |
| **物模型层** | 九井云属性上报格式兼容 | 3 | 每次 PR / 定期 |
| **对抗层** | 边界/异常/高并发 | 8 | 定期 / 发布前 |
| **总计** | | **35** | |

---

## 3. 冐烟层（Smoke）

> 通过 `pytest` 自动执行，量化判分。测试数据使用九井云真实格式。

> **⚠️ 冒烟测试脚本说明**：
> - `scripts/test/smoke.sh` — 统一冒烟测试脚本，支持两种模式：
>   - `TEST_MODE=jiujingyun bash smoke.sh`（默认）：九井云格式
>   - `TEST_MODE=simple bash smoke.sh`：简单格式
> - `testcases.md` 要求使用九井云真实格式

### 3.1 冒烟测试（SMOKE）

#### TC-SMOKE-001: 服务健康检查

| 字段 | 内容 |
|------|------|
| case_id | TC-SMOKE-001 |
| case_name | 服务健康检查 |
| category_level1 | 冒烟 |
| category_level2 | 核心链路 |
| mode | 单轮 |
| **question** | 发送 `GET /health`，验证服务是否正常运行 |
| **expected_answer** | HTTP 200，响应体包含 `status=healthy`、`mqtt_connected=true`、`influxdb_connected=true` |
| focus_metrics | 可用性 |
| **evaluation_criteria** | 响应状态码 200；响应时间 < 500ms；JSON 字段有效 |
| **evaluation_script** | `curl -s http://localhost:8080/health \| jq '.status == "healthy" and .mqtt_connected == true and .influxdb_connected == true'` |
| **reference** | [2.jiujing_mqtt连接.md](../reference/2.jiujing_mqtt连接.md) — 连接参数验证 |

#### TC-SMOKE-002: 设备列表查询

| 字段 | 内容 |
|------|------|
| case_id | TC-SMOKE-002 |
| case_name | 设备列表查询 |
| category_level1 | 冒烟 |
| category_level2 | 核心链路 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices`，验证能否返回已注入的设备列表 |
| **expected_answer** | HTTP 200，`success=true`，`data` 数组包含测试设备 |
| focus_metrics | 正确性 |
| **evaluation_criteria** | 状态码 200；`success` 字段为 `true`；`data` 数组非空且包含预设设备 ID |
| **evaluation_script** | `curl -s http://localhost:8080/api/v1/devices \| jq '.success == true and ([.data[].device_id] \| contains(["sensor-001","sensor-002"]))'` |
| **reference** | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — 设备标识与属性含义 |

#### TC-SMOKE-003: 设备遥测数据查询

| 字段 | 内容 |
|------|------|
| case_id | TC-SMOKE-003 |
| case_name | 设备遥测数据查询 |
| category_level1 | 冒烟 |
| category_level2 | 核心链路 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices/{device_id}/telemetry`，验证遥测数据是否正确存储 |
| **expected_answer** | HTTP 200，`success=true`，`data` 数组非空 |
| focus_metrics | 正确性 |
| **evaluation_criteria** | 状态码 200；`success==true`；遥测数据中能找到注入的 sensor-001 数据 |
| **evaluation_script** | `curl -s "http://localhost:8080/api/v1/devices/sensor-001/telemetry?limit=10" \| jq '[.data[] \| select(.device_id == "sensor-001" and .sensor_type == "temperature")] \| length > 0'` |
| **reference** | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — 属性上报主题与数据格式 |

---

### 3.2 能力测试（CAPABILITY）

#### TC-CAP-001: 设备详情查询

| 字段 | 内容 |
|------|------|
| case_id | TC-CAP-001 |
| case_name | 设备详情查询 |
| category_level1 | 能力 |
| category_level2 | API功能 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices/{device_id}`，验证能否获取设备最新遥测 |
| **expected_answer** | HTTP 200，`success=true`，返回 `latest` 记录 |
| focus_metrics | 正确性 |
| **evaluation_criteria** | 状态码 200；返回的 `latest` 记录包含 `device_id`、`sensor_type`、`value` |
| **evaluation_script** | `curl -s http://localhost:8080/api/v1/devices/sensor-001 \| jq '.success == true and .device_id == "sensor-001" and .latest != null'` |
| **reference** | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — DeviceID 等属性含义 |

#### TC-CAP-002: 设备状态查询

| 字段 | 内容 |
|------|------|
| case_id | TC-CAP-002 |
| case_name | 设备状态查询 |
| category_level1 | 能力 |
| category_level2 | API功能 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices/{device_id}/status`，验证能否获取设备最新状态 |
| **expected_answer** | HTTP 200，`success=true`，返回最新遥测记录 |
| focus_metrics | 正确性 |
| **evaluation_criteria** | 状态码 200；`data` 数组包含 1 条记录 |
| **evaluation_script** | `curl -s http://localhost:8080/api/v1/devices/sensor-001/status \| jq '.success == true and (.data \| length) >= 1'` |
| **reference** | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — OnlineInfo 在线信息字段 |

#### TC-CAP-003: 时间范围查询

| 字段 | 内容 |
|------|------|
| case_id | TC-CAP-003 |
| case_name | 时间范围查询 |
| category_level1 | 能力 |
| category_level2 | API功能 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices/{device_id}/telemetry?start=-1h&end=now`，验证时间范围过滤 |
| **expected_answer** | HTTP 200，所有返回记录的 `time` 在过去 1 小时内 |
| focus_metrics | 正确性 |
| **evaluation_criteria** | 状态码 200；所有记录的 `_time` 在指定时间范围内 |
| **evaluation_script** | `curl -s "http://localhost:8080/api/v1/devices/sensor-001/telemetry?start=-1h&limit=10" \| jq '[.data[] \| select((.time // ._time) != null)] \| length > 0'` |
| **reference** | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — 属性上报间隔30s |

#### TC-CAP-004: 分页限制

| 字段 | 内容 |
|------|------|
| case_id | TC-CAP-004 |
| case_name | 分页限制 |
| category_level1 | 能力 |
| category_level2 | API功能 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices/{device_id}/telemetry?limit=5`，验证返回记录数不超过 limit |
| **expected_answer** | HTTP 200，`data` 数组长度 ≤ 5 |
| focus_metrics | 正确性 |
| **evaluation_criteria** | 状态码 200；`data` 数组长度 ≤ 5 |
| **evaluation_script** | `curl -s "http://localhost:8080/api/v1/devices/sensor-001/telemetry?limit=5" \| jq '.data \| length <= 5'` |
| **reference** | [openclaw/iot-mqtt-bridge/references/tools.md](../../openclaw/iot-mqtt-bridge/references/tools.md) — query_device_telemetry limit参数说明 |

#### TC-CAP-005: 不存在的设备查询

| 字段 | 内容 |
|------|------|
| case_id | TC-CAP-005 |
| case_name | 不存在的设备查询 |
| category_level1 | 能力 |
| category_level2 | 边界条件 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices/nonexistent-device`，验证对未知设备的处理 |
| **expected_answer** | HTTP 200，`success=true`，`latest=null` 或 `data=[]` |
| focus_metrics | 鲁棒性 |
| **evaluation_criteria** | 不返回 404；优雅降级 |
| **evaluation_script** | `curl -s http://localhost:8080/api/v1/devices/nonexistent-device \| jq '.success == true'` |
| **reference** | [openclaw/iot-mqtt-bridge/references/agent-guidelines.md](../../openclaw/iot-mqtt-bridge/references/agent-guidelines.md) — 无数据排查建议 |

#### TC-CAP-006: 九井云物模型格式存储验证

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-CAP-006 | 九井云物模型格式存储验证 | 能力 | 端到端 | 3轮 | 1 | 发布九井云标准格式的物模型属性到 `/system/jiujing_cpe/cpe-sn-001/thing/property/post`，包含 MobileNetwork1、CPU、UseMemory 等 30+ 字段，等待 batch flush（10s） | MQTT 发布成功，返回 code=0，无错误 | | | | |
| TC-CAP-006 | | | | | 2 | 查询设备列表，确认 cpe-sn-001 已出现 | HTTP 200，`success=true`，`data` 数组包含 `device_id=cpe-sn-001` | | | | |
| TC-CAP-006 | | | | | 3 | 查询设备 cpe-sn-001 的最新遥测，验证 CPU、UseMemory、MobileNetwork1.RSRP 等字段值是否正确还原 | HTTP 200，`latest.params.CPU.value`、`latest.params.UseMemory.value`、`latest.params.MobileNetwork1.RSRP` 等字段存在且值合理，无解析错误 | 正确性、完整性 | 1) 设备出现在设备列表<br>2) 遥测数据包含九井云格式字段（MobileNetwork1_RSRP 等）<br>3) CPU/UseMemory 等核心属性值匹配发布值 | `curl -s http://localhost:8080/api/v1/devices/cpe-sn-001 \| jq '.success == true and .latest.params.CPU.value == "0.35"'` | [2.jiujing_mqtt连接.md](../reference/2.jiujing_mqtt连接.md) — 通信方式一：属性上报；[3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — 上报主题与格式 |

#### TC-CAP-007: 多网络接口数据解析

| 字段 | 内容 |
|------|------|
| case_id | TC-CAP-007 |
| case_name | 多网络接口数据解析 |
| category_level1 | 能力 |
| category_level2 | 数据格式 |
| mode | 单轮 |
| **question** | 发布包含 MobileNetwork1 和 MobileNetwork2（双卡）数据的九井云格式消息，验证两个网络接口的数据都能被正确解析 |
| **expected_answer** | 遥测数据中同时包含 MobileNetwork1 和 MobileNetwork2 的字段（Status、RSRP、IPV4 等） |
| focus_metrics | 正确性 |
| **evaluation_criteria** | 存储后查询返回的数据能正确还原，不出现乱码或截断 |
| **evaluation_script** | `curl -s "http://localhost:8080/api/v1/devices/${DEVICE_KEY}/telemetry?limit=10" \| jq '[.data[] \| select(.MobileNetwork1_RSRP != null)] \| length > 0'` |
| **reference** | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — 嵌套JSON结构的转义风险 |

#### TC-CAP-008: 批处理 flush 验证

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-CAP-008 | 批处理 flush 验证 | 能力 | 性能 | 3轮 | 1 | 在 1 秒内通过 MQTT 发布 100 条九井云格式遥测消息到 `devices/sensor-batch/telemetry` | MQTT 发布全部成功，返回 code=0，无丢消息错误 | | | | |
| TC-CAP-008 | | | | | 2 | 等待 10 秒，让 batch 队列 flush 到 InfluxDB | 等待完成，无超时错误 | | | | |
| TC-CAP-008 | | | | | 3 | 查询 sensor-batch 设备的遥测数据，limit=200，验证已写入的数据条数 | HTTP 200，`data` 数组长度 = 100（或受 limit 限制的最大值），所有消息已写入 | 完整性 | 发送 100 条，等待 flush_interval(10s)，查询 limit=200，数据完整（长度=100） | `curl -s "http://localhost:8080/api/v1/devices/sensor-batch/telemetry?limit=200" \| jq '.data \| length == 100'` | [config.yaml](../../config.yaml) — batch.size=5000, flush_interval=10 |

---

## 5. 运维操作层（Operations）

> 本层测试通过 OpenClaw Agent 对九井云 MQTT 设备进行运维操作，验证"平台下发→设备订阅→执行回复"的完整闭环。
>
> 协议模式：平台发布到 `/system/${productKey}/${deviceKey}/thing/service/${serviceName}`，设备订阅后回复到 `${serviceName}_reply`。
>
> **⚠️ 执行前提**：需要模拟九井云设备行为（订阅命令主题 + 发布回复到 `_reply` 主题）。可使用 `scripts/test_data/simulate_device_stream.py` 或自行实现设备模拟器。
>
> 参考：[2.jiujing_mqtt连接.md](../reference/2.jiujing_mqtt连接.md) — 通信方式二；[4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) — 功能列表与参数格式

### TC-OPS-001: 修改设备名称（SetDeviceName）

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-OPS-001 | 修改设备名称（SetDeviceName） | 运维操作 | 身份管理 | 多轮 | 1 | 修改 Kasa Smart Plug 01 这个设备的名称，改为 Kasa Smart Plug 01_renamed | 设备回复 `code=200`、`data.Code="0"`、`data.Result` 非空、`id` 与下发 id 一致 | 正确性、闭环完整性 | 1) 设备收到下发的 DeviceName 参数正确；2) 回复的 `id` 匹配下发 id；3) `code==200`；4) `data.Code=="0"` 表示执行成功 | 订阅 `_reply` 主题，验证 JSON 中 `code==200 and .id == "<下发id>" and .data.Code == "0"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) §1 — SetDeviceName 下发与回复格式 |

### TC-OPS-002: NTP 配置下发（SetNTPConfig）

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-OPS-002 | NTP 配置下发（SetNTPConfig） | 运维操作 | 时钟同步 | 多轮 | 1 | 配置 NTP 同步服务器为 ntp.aliyun.com，并启用 NTP 功能 | 设备回复 `code=200`，`data.Code="0"`；后续属性上报中可观察到时间同步信息变化 | 正确性、配置生效 | 1) 下发参数 NtpSwitch/NtpServer1 正确到达设备；2) 回复 code=200；3) 若属性上报周期正常，OnlineInfo.DeviceTime 反映同步 | 订阅 `_reply` 主题，验证 `code==200 and .data.Code == "0"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) §2 — SetNTPConfig 参数与回复；[3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — OnlineInfo.DeviceTime |

### TC-OPS-003: 设备定时重启（DeviceReboot）

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-OPS-003 | 设备定时重启（DeviceReboot） | 运维操作 | 生命周期 | 多轮 | 1 | 设置设备每天凌晨 3 点定时重启 | 设备回复 `code=200`，`data.Code="0"`，重启计划已设置 | 正确性、安全约束 | 1) Rule=2/Hour=3/Minutes=0 参数正确到达；2) 回复 code=200；3) 不验证实际重启（安全约束），只验证命令接受 | 订阅 `_reply` 主题，验证 `code==200 and .data.Code == "0"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) §8 — DeviceReboot Rule/Day/Week/Hour/Minutes 参数；[8.jiujing_平台告警触发机制.md](../reference/8.jiujing_平台告警触发机制.md) — 告警ID3: 30s无上报触发离线告警 |

### TC-OPS-004: WAN 优先级调整（WANPriority）

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-OPS-004 | WAN 优先级调整（WANPriority） | 运维操作 | 网络管理 | 多轮 | 1 | 调整 WAN 优先级顺序，将 nrWan 接口设为第一优先级 | 设备回复 `code=200`，`data.Code="0"` | 正确性 | 1) Interface 枚举值在合法范围内（nrWan/nrWanb/wlan5G/wiredWan1 等）；2) Priority 为 int 类型；3) 回复成功 | 订阅 `_reply` 主题，验证 `code==200 and .data.Code == "0"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) §12 — WANPriority Interface枚举与Priority |

### TC-OPS-005: 移动网络配置（MobileNetworkConfig）

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-OPS-005 | 移动网络配置（MobileNetworkConfig） | 运维操作 | 网络管理 | 多轮 | 1 | 配置移动网络，使用 ID=1，APN 设为 cmnet，认证方式为不认证 | 设备回复 `code=200`，`data.Code="0"`；后续 MobileNetwork1 属性上报可反映拨号状态 | 正确性、配置生效 | 1) 多路会话 Id=1\|2\|3\|4 合法；2) AuthMethod 枚举 0\|1\|2\|3 合法；3) 回复成功 | 订阅 `_reply` 主题，验证 `code==200 and .data.Code == "0"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) §14 — MobileNetworkConfig Id/Switch/APN/AuthMethod/PreferredNetworkMode 参数；[3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — MobileNetwork1 属性上报 |

### TC-OPS-006: SIM 卡切换（SIMConfig）

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-OPS-006 | SIM 卡切换（SIMConfig） | 运维操作 | SIM管理 | 多轮 | 1 | 设置 SIM 卡为自动切换模式（MainCardSelect=3），并绑定 SIM 卡 1 | 设备回复 `code=200`，`data.Code="0"` | 正确性 | 1) MainCardSelect 枚举 1\|2\|3\|4\|5 合法；2) BindSIMCard1=0\|1 合法；3) 回复成功 | 订阅 `_reply` 主题，验证 `code==200 and .data.Code == "0"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) §19 — SIMConfig MainCardSelect/PIN/PUK/BindSIMCard 参数；[3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — SIMCard1/SIMCard2 属性上报 |

### TC-OPS-007: 双机热备配置（HotStandby）

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-OPS-007 | 双机热备配置（HotStandby） | 运维操作 | 高可用 | 多轮 | 1 | 配置双机热备功能，角色设为 MASTER，VRID 为 10，节点优先级为 100 | 设备回复 `code=200`，`data.Code="0"` | 正确性、安全 | 1) Role 枚举 MASTER\|BACKUP 合法；2) 关键参数（VRID, NodePriority, HeartbeatInterval）类型正确；3) 回复成功 | 订阅 `_reply` 主题，验证 `code==200 and .data.Code == "0"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) §20 — HotStandby Switch/Role/VRID/NodePriority/HeartbeatInterval 参数 |

### TC-OPS-008: VLAN 配置（VLANConfig）

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-OPS-008 | VLAN 配置（VLANConfig） | 运维操作 | 二层网络 | 多轮 | 1 | 配置 VLAN，VLAN ID 为 100，Port0 和 CPU 设为 tagged 模式 | 设备回复 `code=200`，`data.Code="0"` | 正确性 | 1) Action 枚举 edit\|delete 合法；2) VLANID 字段正确；3) 回复成功 | 订阅 `_reply` 主题，验证 `code==200 and .data.Code == "0"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) §21 — VLANConfig Action/VLANID/Port0-Port5/CPU 参数 |

---

## 6. 生命周期层（Lifecycle）

> 本层测试 OTA 升级、配置更新和文件获取等多步交互流程。
>
> **⚠️ 执行说明**：生命周期测试涉及平台与设备的多轮 MQTT 消息交互，需要：
> 1. Agent 订阅相关 reply/process 主题
> 2. Agent 通过 HTTP API 下发命令
> 3. 模拟设备按协议流程发布各阶段回复
>
> 参考：[2.jiujing_mqtt连接.md](../reference/2.jiujing_mqtt连接.md) — 通信方式三/四/五

### TC-LIFE-001: OTA 升级全流程

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-----------|
| TC-LIFE-001 | OTA 升级全流程 | 生命周期 | OTA升级 | 4轮 | 1 | 对设备 cpe-sn-001 执行 OTA 升级，升级包地址是 http://example.com/firmware.bin，版本 1.0.1 | 命令下发成功，返回 request_id，等待设备确认 | | | |
| TC-LIFE-001 | | | | | 2 | 检查设备 cpe-sn-001 的 OTA 升级是否已确认 | 设备已确认，返回 detail_id=xxx，ota/get/reply 收到确认消息 | | | |
| TC-LIFE-001 | | | | | 3 | 检查设备 cpe-sn-001 的 OTA 升级进度 | ota/upgrade/process 返回当前 step=50（或其他非100值），升级进行中 | | | |
| TC-LIFE-001 | | | | | 4 | 最终检查设备 cpe-sn-001 的 OTA 升级是否完成 | ota/upgrade/process 返回 step=100，fail 为空，升级成功完成 | 完整性、流程正确性 | 1) detail_id 在各轮保持一致<br>2) step 从低到高单调递增<br>3) 最终 step=100 且 fail 为空<br>4) 全程服务不崩溃 | [5.jiujing_ota升级.md](../reference/5.jiujing_ota升级.md) — OTA 三步交互流程与字段定义 |

### TC-LIFE-002: OTA 升级失败

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-----------|
| TC-LIFE-002 | OTA 升级失败 | 生命周期 | OTA升级异常 | 3轮 | 1 | 对设备 cpe-sn-001 执行 OTA 升级，升级包地址是 http://example.com/firmware.bin，版本 1.0.1 | 命令下发成功，返回 request_id，等待设备确认 | | | |
| TC-LIFE-002 | | | | | 2 | 检查设备 cpe-sn-001 的 OTA 升级是否已确认 | 设备已确认，返回 detail_id=xxx，ota/get/reply 收到确认消息 | | | |
| TC-LIFE-002 | | | | | 3 | 检查设备 cpe-sn-001 的 OTA 升级最终状态 | ota/upgrade/process 返回 step=xx（<100），fail 非空（如"存储空间不足"） | 鲁棒性、异常处理 | 1) fail 字段非空<br>2) step < 100<br>3) 平台能记录失败原因且不崩溃 | [5.jiujing_ota升级.md](../reference/5.jiujing_ota升级.md) — upgrade/process fail字段说明 |

### TC-LIFE-003: 批量配置下发

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-----------|
| TC-LIFE-003 | 批量配置下发 | 生命周期 | 配置管理 | 4轮 | 1 | 对设备 cpe-sn-001 下发批量配置更新，配置文件地址是 http://example.com/config.bin | 命令下发成功，返回 detail_id=xxx，等待设备确认 | | | |
| TC-LIFE-003 | | | | | 2 | 检查设备 cpe-sn-001 的配置更新是否已确认 | profile/get/reply 收到确认消息，detail_id 与下发一致 | | | |
| TC-LIFE-003 | | | | | 3 | 检查设备 cpe-sn-001 的配置更新进度 | profile/upgrade/process 返回当前 step=xx（如 50），更新进行中 | | | |
| TC-LIFE-003 | | | | | 4 | 最终检查设备 cpe-sn-001 的配置更新是否完成 | profile/upgrade/process 返回 step=100，fail 为空，配置更新成功 | 完整性、流程正确性 | 1) detail_id 在各轮保持一致<br>2) step 最终=100<br>3) fail 为空<br>4) 全程服务不崩溃 | [7.jiujing_批量配置和设备配置更新.md](../reference/7.jiujing_批量配置和设备配置更新.md) — 配置更新三步流程与字段定义 |

### TC-LIFE-004: 获取设备配置文件

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-----------|
| TC-LIFE-004 | 获取设备配置文件 | 生命周期 | 文件获取 | 2轮 | 1 | 获取设备 cpe-sn-001 的配置文件 | 请求已发送，profile/download/process 返回 download_url 或 fail | | | |
| TC-LIFE-004 | | | | | 2 | 查看配置文件获取结果 | profile/download/process 返回 download_url 非空，fail 为空，配置文件已上传 | 正确性 | 1) download_url 非空<br>2) fail 为空<br>3) 文件内容有效 | [6.jiujing_获取设备配置文件或日志文件.md](../reference/6.jiujing_获取设备配置文件或日志文件.md) — file_type/download_url/detail_id 定义 |

### TC-LIFE-005: 获取设备日志文件

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-----------|
| TC-LIFE-005 | 获取设备日志文件 | 生命周期 | 文件获取 | 2轮 | 1 | 获取设备 cpe-sn-001 的日志文件 | 请求已发送，profile/download/process 返回 download_url 或 fail | | | |
| TC-LIFE-005 | | | | | 2 | 查看日志文件获取结果 | profile/download/process 返回 download_url 非空，file_type=device_log，fail 为空 | 正确性 | 1) download_url 非空<br>2) file_type=device_log<br>3) fail 为空 | [6.jiujing_获取设备配置文件或日志文件.md](../reference/6.jiujing_获取设备配置文件或日志文件.md) — file_type=device_log 与 upload_url/request_token |

---

## 7. 物模型层（Property Model）

> 本层测试九井云真实物模型属性上报格式在 Bridge 链路中的兼容性。
> Bridge 原生格式为简单 JSON（device_id/sensor_type/value），九井云格式为嵌套 params 结构。
> 关键验证：嵌套 JSON → Line Protocol → InfluxDB → API 查询还原。

> 参考：[3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — 完整物模型30+属性字段及上报格式

### TC-PROP-001: 完整物模型属性上报与查询还原

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-PROP-001 | 完整物模型属性上报与查询还原 | 物模型 | 格式兼容 | 3轮 | 1 | 发布包含 30+ 属性的九井云物模型完整 JSON 到 `/system/jiujing_cpe/cpe-sn-001/thing/property/post`，等待 batch flush（10s） | MQTT 发布成功，返回 code=0，无解析错误 | | | | |
| TC-PROP-001 | | | | | 2 | 查询设备列表，确认 cpe-sn-001 已出现且可查询 | HTTP 200，`success=true`，`data` 数组包含 `device_id=cpe-sn-001` | | | | |
| TC-PROP-001 | | | | | 3 | 查询 cpe-sn-001 最新遥测数据，验证 DeviceID、DeviceSWVersion、CPU、UseMemory、DiskUsage、ModuleTemperature 等核心属性值正确还原 | HTTP 200，`latest` 包含 CPU、UseMemory、DiskUsage 等字段且值与发布一致，无解析错误 | 正确性、完整性 | 1) Bridge 能解析九井云嵌套 JSON 格式<br>2) 关键扁平属性（CPU/UseMemory/DiskUsage）值还原正确<br>3) 设备出现在设备列表 | `curl -s http://localhost:8080/api/v1/devices/cpe-sn-001 \| jq '.success == true and .latest != null'` | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — 完整上报 JSON 格式与30+属性字段 |

### TC-PROP-002: 嵌套结构属性解析

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-PROP-002 | 嵌套结构属性解析 | 物模型 | 数据格式 | 3轮 | 1 | 发布包含 SIMCard1 和 MobileNetwork1 嵌套结构的九井云格式属性数据，等待 batch flush（10s） | MQTT 发布成功，返回 code=0，无解析错误 | | | | |
| TC-PROP-002 | | | | | 2 | 查询 cpe-sn-001 的最新遥测数据，验证 SIMCard1.Status、SIMCard1.SIMCardSelect 等 SIMCard 嵌套字段是否正确还原 | HTTP 200，`latest.params.SIMCard1.Status`、`latest.params.SIMCard1.SIMCardSelect` 等子字段存在且值合理 | | | | |
| TC-PROP-002 | | | | | 3 | 继续验证 MobileNetwork1.Status、MobileNetwork1.RSRP、MobileNetwork1.SINR 等 MobileNetwork 嵌套字段是否正确还原 | HTTP 200，`latest.params.MobileNetwork1.RSRP`、`latest.params.MobileNetwork1.SINR` 等子字段存在且值合理，无数据丢失 | 正确性、数据完整性 | 1) 嵌套 JSON 不导致解析失败<br>2) 子字段值正确存储<br>3) 无数据丢失 | `curl -s http://localhost:8080/api/v1/devices/cpe-sn-001 \| jq '.latest.params.MobileNetwork1_RSRP != null'` | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — SIMCard/MobileNetwork/WLAN/LAN 嵌套结构 |

### TC-PROP-003: PING 结果单独上报

| 字段 | 内容 |
|------|------|
| case_id | TC-PROP-003 |
| case_name | PING 结果单独上报 |
| category_level1 | 物模型 |
| category_level2 | 数据格式 |
| mode | 单轮 |
| **question** | 上报 PINGResult 数组格式 JSON（含 TTL/Byte/Delay/Server/Sequence + time），验证数组属性能正确解析存储 |
| **expected_answer** | PINGResult 数组被正确解析存储，查询可返回各子字段 |
| focus_metrics | 正确性 |
| **evaluation_criteria** | 1) 数组 JSON 不导致解析失败；2) PINGResult 子字段存储正确 |
| **evaluation_script** | 查询 InfluxDB 中 PINGResult 相关字段 |
| **reference** | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) — PINGResult 数组格式与单独上报规则 |

---

## 8. 对抗层（Adversarial）

#### TC-ADV-001: 非法时间参数

| 字段 | 内容 |
|------|------|
| case_id | TC-ADV-001 |
| case_name | 非法时间参数 |
| category_level1 | 对抗 |
| category_level2 | 异常输入 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices/{device_id}/telemetry?start=invalid&end=invalid`，验证错误处理 |
| **expected_answer** | HTTP 200 或 400，带 `error` 字段说明错误原因，不返回 500 |
| focus_metrics | 鲁棒性 |
| **evaluation_criteria** | 不返回 500 内部错误；返回有意义的错误信息 |
| **evaluation_script** | `curl -s "http://localhost:8080/api/v1/devices/sensor-001/telemetry?start=invalid" \| jq 'has("error")'` |
| **reference** | [openclaw/iot-mqtt-bridge/references/tools.md](../../openclaw/iot-mqtt-bridge/references/tools.md) — start/end 参数说明 |

#### TC-ADV-002: SQL 注入防护

| 字段 | 内容 |
|------|------|
| case_id | TC-ADV-002 |
| case_name | SQL 注入防护 |
| category_level1 | 对抗 |
| category_level2 | 安全 |
| mode | 单轮 |
| **question** | 发送 POST 请求到 /api/v1/query，内容是 `DROP TABLE device_telemetry`，会返回什么？ |
| **expected_answer** | 返回 JSON：success=false，error 说明"SQL 语句仅支持查询操作" |
| **evaluation_criteria** | 1) 返回 success=false<br>2) error 包含"查询"或"不可执行"等关键词<br>3) 不返回 500 |
| **evaluation_script** | `curl -s -X POST http://localhost:8080/api/v1/query -H "Content-Type: application/json" -d '{"sql":"DROP TABLE device_telemetry"}' \| jq '.success == false and (.error | test("查询|不可执行"))'` |
| **reference** | [openclaw/iot-mqtt-bridge/SKILL.md](../../openclaw/iot-mqtt-bridge/SKILL.md) — 不提供 raw SQL 能力约束 |

#### TC-ADV-003: 超大 limit 参数

| 字段 | 内容 |
|------|------|
| case_id | TC-ADV-003 |
| case_name | 超大 limit 参数 |
| category_level1 | 对抗 |
| category_level2 | 边界条件 |
| mode | 单轮 |
| **question** | 发送 `GET /api/v1/devices/{device_id}/telemetry?limit=99999`（超过最大允许值 10000） |
| **expected_answer** | HTTP 200 或 422，返回数据受 max=10000 限制 |
| focus_metrics | 鲁棒性 |
| **evaluation_criteria** | 请求不导致服务崩溃；返回数据量有上限 |
| **evaluation_script** | `curl -s "http://localhost:8080/api/v1/devices/sensor-001/telemetry?limit=99999" \| jq 'if .data then .data \| length <= 10000 else true end'` |
| **reference** | [openclaw/iot-mqtt-bridge/references/tools.md](../../openclaw/iot-mqtt-bridge/references/tools.md) — limit 最大10000 |

#### TC-ADV-004: MQTT QoS 级别处理

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-ADV-004 | MQTT QoS 级别处理 | 对抗 | 异常处理 | 3轮 | 1 | 以 QoS 0 级别发布 MQTT 消息到 `devices/qos-test-device/telemetry`，包含 device_id、sensor_type、value 字段 | MQTT 发布成功，返回 code=0 | | | | |
| TC-ADV-004 | | | | | 2 | 以 QoS 1 级别发布 MQTT 消息到同一主题，验证 QoS 1 的交付保证 | MQTT 发布成功，返回 code=1（QoS 1 acknowledgment） | | | | |
| TC-ADV-004 | | | | | 3 | 以 QoS 2 级别发布 MQTT 消息，验证 QoS 2 的完全交付保证，然后查询 API 验证所有消息都可查到 | MQTT 发布成功，返回 code=2（QoS 2 完成）；API 查询返回所有 QoS 级别的消息 | 可靠性 | 服务不崩溃；不同 QoS 级别消息均可查询 | `curl -s http://localhost:8080/api/v1/devices/qos-test-device/telemetry?limit=10 \| jq '.data \| length >= 0'` | [config.yaml](../../config.yaml) — qos telemetry:1, status:0；[2.jiujing_mqtt连接.md](../reference/2.jiujing_mqtt连接.md) — MQTT连接参数 |

#### TC-ADV-005: 快速批量消息压力测试

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-ADV-005 | 快速批量消息压力测试 | 对抗 | 高并发 | 3轮 | 1 | 在 1 秒内发送 1000 条 MQTT 消息到 `devices/stress-test-device/telemetry`，验证批处理队列不溢出 | MQTT 发布全部成功，无队列溢出错误 | | | | |
| TC-ADV-005 | | | | | 2 | 等待 15 秒，让 batch flush 完成（batch.size=5000，1000 条消息应分批写入） | 等待完成，无超时错误 | | | | |
| TC-ADV-005 | | | | | 3 | 查询服务健康状态和设备遥测数据，验证服务仍然正常运行且数据已写入 | HTTP 200，`status=healthy`，遥测数据可查询，消息已写入 InfluxDB | 稳定性、高并发 | 服务不崩溃；API 不返回错误；所有消息最终写入 | `curl -s http://localhost:8080/health \| jq '.status == "healthy"'` | [config.yaml](../../config.yaml) — batch.size=5000 |

### TC-ADV-006: 设备功能回复超时

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-ADV-006 | 设备功能回复超时 | 对抗 | 运维异常 | 3轮 | 1 | 对设备 cpe-sn-001 下发 SetDeviceName 命令，将设备名称改为 TestDevice，然后模拟设备不回复任何内容 | MQTT 命令发布成功，记录下发但未收到设备回复 | | | | |
| TC-ADV-006 | | | | | 2 | 等待 30 秒，让命令超时 | 等待完成，服务未崩溃 | | | | |
| TC-ADV-006 | | | | | 3 | 查询服务健康状态和设备列表，验证平台在超时后仍能保持运行且不崩溃 | HTTP 200，`status=healthy`，Agent 可通过属性上报间接确认设备是否仍在运行 | 鲁棒性、运维可观测性 | 1) 服务不崩溃<br>2) 超时后 API 正常<br>3) Agent 能识别"命令未确认"状态 | 等待30s后 `curl -s http://localhost:8080/health \| jq '.status == "healthy"'` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) — 服务命令下发与回复模式；[8.jiujing_平台告警触发机制.md](../reference/8.jiujing_平台告警触发机制.md) — 告警ID3: 30s无上报触发离线告警 |

### TC-ADV-007: 设备回复错误码

| case_id | case_name | category_level1 | category_level2 | mode | turn | question | expected_answer | focus_metrics | evaluation_criteria | evaluation_script | reference |
|---------|-----------|-----------------|-----------------|------|------|---------|-----------------|---------------|---------------------|-------------------|-----------|
| TC-ADV-007 | 设备回复错误码 | 对抗 | 运维异常 | 2轮 | 1 | 对设备 cpe-sn-001 下发 SetNTPConfig 命令，然后模拟设备回复执行失败（data.Code="-1"） | 平台接收到设备回复 `data.Code="-1"`，记录失败状态，不崩溃 | | | | |
| TC-ADV-007 | | | | | 2 | 查询命令执行状态，验证平台能正确区分成功(Code=0)和失败(Code≠0)，且不因错误码导致异常 | 平台能记录 `data.Code != "0"` 的失败状态，服务仍健康 | 鲁棒性 | 1) 回复被接收<br>2) `data.Code="-1"` 不导致异常<br>3) Agent 能区分成功(Code=0)和失败(Code≠0) | 验证 _reply 主题收到回复且 `data.Code == "-1"` | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) — 回复格式 data.Code 执行状态码（0=成功，非0=失败） |

### TC-ADV-008: 无效功能命令 serviceName

| 字段 | 内容 |
|------|------|
| case_id | TC-ADV-008 |
| case_name | 无效功能命令 serviceName |
| category_level1 | 对抗 |
| category_level2 | 运维异常 |
| mode | 单轮 |
| **question** | 调用设备功能时使用一个不存在的 serviceName "SetInvalidService"，会返回什么结果？ |
| **expected_answer** | MQTT 发布到服务主题后，不会有 _reply 主题的回复（设备不订阅该主题），Agent 会等待超时 |
| **evaluation_criteria** | 1) MQTT 发布返回成功（主题合法）<br>2) 无 _reply 回复<br>3) 服务不崩溃，仍能响应后续合法请求 |
| **evaluation_script** | 发布后等待 15s，验证 health 仍为 healthy，且无 _reply 消息 |
| **reference** | [4.jiujing_设备功能.md](../reference/4.jiujing_设备功能.md) — serviceName 合法枚举列表；[2.jiujing_mqtt连接.md](../reference/2.jiujing_mqtt连接.md) — 设备订阅指定 serviceName 主题 |

---

## 9. 告警关联索引

> 告警触发机制与测试用例的交叉验证关系。
> 参考：[8.jiujing_平台告警触发机制.md](../reference/8.jiujing_平台告警触发机制.md)

| 告警ID | 告警名称 | 触发规则 | 关联测试用例 |
|--------|----------|----------|-------------|
| 1 | CPU占用率过高 | CPU>95% | TC-PROP-001（CPU属性上报验证） |
| 2 | 内存占用率过高 | UseMemory>85% | TC-PROP-001（UseMemory属性上报） |
| 3 | 网关离线 | 30s无上报 | TC-ADV-006（回复超时→离线检测） |
| 4 | 连接中断 | 探测服务器状态=0 | TC-OPS-005（移动网络配置影响连通性） |
| 5 | 时延过高 | PingDelay>100ms | TC-PROP-003（PINGResult上报） |
| 6 | 蜂窝信号弱 | RSRP<-105dBm | TC-PROP-002（MobileNetwork1.RSRP解析） |
| 7 | 蜂窝信号干扰大 | SINR<5dB | TC-PROP-002（MobileNetwork1.SINA解析） |
| 8 | LAN口连接中断 | LAN口探测30s不通 | TC-OPS-008（VLAN配置影响LAN口） |
| 9 | 模组温度过高 | 温度>80℃ | TC-PROP-001（ModuleTemperature属性） |

---

## 10. 执行指南

### 10.1 OpenClaw Agent 执行流程

```
1. 初始化阶段
   ├── 启动 InfluxDB（start_influxdb_native.sh）
   ├── 启动 MQTT Broker（start_nanomq.sh）
   ├── 启动 Bridge Service（start_bridge.sh）
   ├── 初始化简单 sensor 测试数据（sensor-001, sensor-002）
   └── 初始化九井云物模型测试数据（cpe-sn-001, cpe-sn-002）

2. 执行阶段（冒烟 → 能力 → 运维操作 → 生命周期 → 物模型 → 对抗）
   ├── 冒烟层：3 个用例（快速失败检测）
   ├── 能力层：8 个用例（API 功能验证）
   ├── 运维操作层：8 个用例（设备功能下发闭环）
   ├── 生命周期层：5 个用例（OTA/配置/文件多步交互）
   ├── 物模型层：3 个用例（九井云格式兼容）
   └── 对抗层：8 个用例（边界与异常）

3. 清理阶段
   └── 查询验证后清理测试数据
```

### 10.2 运维操作层特殊执行要求

运维操作层测试需要模拟设备端行为，OpenClaw Agent 需同时扮演：

- **平台角色**：发布服务命令到下发主题
- **设备角色**：订阅下发主题，发布回复到 `_reply` 主题

执行模式：Agent 先启动 MQTT 订阅监听 `_reply` 主题，然后发布命令到服务主题，等待回复并验证。

### 10.3 测试超时配置

| 操作 | 超时 |
|------|------|
| HTTP API 调用 | 5s |
| MQTT 消息发布 | 3s |
| Batch flush 等待 | 15s |
| 设备功能回复等待 | 30s |
| OTA/配置更新全流程 | 120s |
| 全链路端到端 | 30s |

### 10.4 通过/失败判定

- **PASS**：所有 `evaluation_script` 返回 `true`
- **FAIL**：任意 `evaluation_script` 返回 `false` 或服务返回 5xx
- **ERROR**：服务不可用（连接超时、端口未开放）
- **OPS_PASS**：运维操作层额外判定 — 设备回复 `code==200 and data.Code=="0"`
- **OPS_FAIL**：运维操作层 — 回复 `code!=200` 或 `data.Code!="0"` 或超时无回复

---

## 13. OpenClaw 端到端测试用例集

> 本节整合可直接通过 OpenClaw Agent 执行的端到端测试用例，验证 Agent 与 Bridge 服务、MQTT Broker、InfluxDB 的完整交互。
>
> **执行方式**：通过 OpenClaw Agent 的自然语言交互驱动。Agent 理解用户意图后，调用 Bridge API/MQTT 与设备/数据库交互，返回用户友好的回答。
>
> **驱动方式**：
> - 方式 A：在 Dashboard UI 或 IM 中由用户直接与 Agent 对话
> - 方式 B：通过 openclaw CLI 模拟用户提问：`openclaw agent --agent <agent-name> --message "查询设备 cpe-sn-001 的状态"`（不需要出现任何 adapter.sh 等内部工具名）

### 13.1 环境准备

```bash
# 1. 启动 InfluxDB
bash scripts/start/influxdb.sh
bash scripts/init/influxdb_v2.sh

# 2. 启动 MQTT Broker
bash scripts/start/nanomq.sh

# 3. 启动 Bridge Service
bash scripts/start/bridge.sh

# 4. 设置环境变量
export OPENCLAW_ADAPTER_BASE_URL=http://localhost:8080
```

### 13.2 端到端测试用例

> **⚠️ E2E 测试原则**：以下用例模拟**真实企业用户**与 OpenClaw Agent 的自然语言交互。测试输入是用户在 Dashboard UI 或 IM 中说的话，而非技术命令。所有技术实现细节（MQTT Topic、adapter.sh、payload 字段）不对用户暴露。
>
> **原则详情**：
> - ✅ `question` = 用户自然语言（如"现在有哪些设备在线？"）
> - ❌ `question` ≠ MQTT Topic、adapter.sh 命令、payload 字段
> - `steps` 描述 Agent 内部行为，但仅限"理解意图→调用工具→返回结果"的高层描述，不暴露内部实现
> - `expected_answer` 是用户期望看到的回答，而非 `{code:200, data.Code:"0"}` 等技术细节

#### E2E-001: 九井云物模型属性上报 → InfluxDB 存储 → 查询还原

| 字段 | 内容 |
|------|------|
| case_id | E2E-001 |
| case_name | 九井云物模型属性上报与查询还原 |
| category_level1 | OpenClaw E2E |
| category_level2 | 数据流验证 |
| mode | 多轮 |
| **question** | "我的设备 sensor-001 刚上报了数据，帮我确认一下有没有存下来？" |
| **steps** | 1. 模拟设备上报九井云格式属性（Agent 无感，自动由 Bridge 处理）<br>2. Agent 等待 batch flush（10s）<br>3. Agent 查询 sensor-001 的遥测数据<br>4. Agent 验证返回数据包含 DeviceID、CPU、UseMemory、MobileNetwork1.RSRP 等字段 |
| **expected_answer** | "sensor-001 的遥测数据已存储，最新记录包含：DeviceID=sensor-001、CPU=45%、UseMemory=128MB、MobileNetwork1.RSRP=-85dBm" |
| **focus_metrics** | 正确性、完整性 |
| **evaluation_criteria** | 1) 设备出现在列表<br>2) 遥测数据包含九井云格式嵌套字段<br>3) Agent 回答包含关键字段值 |
| **reference** | `TEST_MODE=jiujingyun bash scripts/test/smoke.sh` |

#### E2E-002: 服务状态检查与设备查询

| 字段 | 内容 |
|------|------|
| case_id | E2E-002 |
| case_name | 服务状态检查与设备查询 |
| category_level1 | OpenClaw E2E |
| category_level2 | 集成验证 |
| mode | 单轮 |
| **question** | "系统现在正常运行吗？有哪些设备连上来了？" |
| **steps** | 1. Agent 检查服务健康状态<br>2. Agent 查询设备列表<br>3. Agent 返回用户友好的状态汇总 |
| **expected_answer** | "服务状态正常。已连接 2 台设备：sensor-001（温度传感器）、cpe-sn-001（ CPE 网关）" |
| **focus_metrics** | 集成正确性 |
| **evaluation_criteria** | 1) Agent 确认服务健康<br>2) 返回设备列表非空<br>3) 回答包含设备名称/类型 |
| **reference** | TC-SMOKE-001、TC-SMOKE-002 |

#### E2E-003: 设备功能下发 → 回复验证（需设备模拟）

| 字段 | 内容 |
|------|------|
| case_id | E2E-003 |
| case_name | 设备功能下发与回复闭环 |
| category_level1 | OpenClaw E2E |
| category_level2 | 双向交互 |
| mode | 多轮 |
| **question** | "帮我把 cpe-sn-001 的设备名称改成 TestRouter" |
| **steps** | 1. Agent 理解用户意图（下发 SetDeviceName 命令）<br>2. Agent 通过 Bridge API 下发命令到 CPE<br>3. 模拟设备收到命令后发布回复<br>4. Agent 接收并匹配回复，通过 WebSocket 推送结果给用户 |
| **expected_answer** | "已将 cpe-sn-001 的设备名称修改为 TestRouter，设备已确认执行成功" |
| **focus_metrics** | 正确性、闭环完整性 |
| **evaluation_criteria** | 1) 命令下发成功<br>2) 设备回复正确<br>3) Agent 推送结果给用户<br>4) 全流程不崩溃 |
| **reference** | TC-OPS-002 |

#### E2E-004: OTA 升级全流程（需设备模拟）

| 字段 | 内容 |
|------|------|
| case_id | E2E-004 |
| case_name | OTA 升级全流程 |
| category_level1 | OpenClaw E2E |
| category_level2 | 生命周期 |
| mode | 4轮 |
| **question** | "对 cpe-sn-001 执行 OTA 升级到版本 1.0.1" |
| **steps** | 1. Agent 理解用户意图，启动 OTA 升级流程<br>2. Agent 下发升级请求（version/url/sign/pkg_name/detail_id）<br>3. Agent 订阅 ota/get/reply，验证 detail_id 匹配<br>4. 模拟设备发布确认<br>5. Agent 订阅 ota/upgrade/process，实时向用户播报进度（step 递增）<br>6. 升级完成后 Agent 告知用户结果 |
| **expected_answer** | "正在对 cpe-sn-001 执行 OTA 升级（目标版本 1.0.1）... 设备已确认，开始下载... 升级进度：50%... 升级完成，版本已更新至 1.0.1" |
| **focus_metrics** | 完整性、流程正确性 |
| **evaluation_criteria** | 1) detail_id 各轮一致<br>2) step 单调递增（0→100）<br>3) 最终 step=100 且 fail 为空<br>4) Agent 实时播报进度 |
| **reference** | TC-LIFE-001 |

#### E2E-005: 批量配置下发（需设备模拟）

| 字段 | 内容 |
|------|------|
| case_id | E2E-005 |
| case_name | 批量配置下发全流程 |
| category_level1 | OpenClaw E2E |
| category_level2 | 生命周期 |
| mode | 4轮 |
| **question** | "给 cpe-sn-001 下发批量配置更新" |
| **steps** | 1. Agent 理解用户意图，启动配置更新流程<br>2. Agent 下发配置更新请求<br>3. Agent 订阅 profile/get/reply，验证 detail_id 匹配<br>4. 模拟设备发布确认<br>5. Agent 订阅 profile/upgrade/process，验证 step=100<br>6. 配置完成后 Agent 告知用户结果 |
| **expected_answer** | "正在对 cpe-sn-001 下发配置更新... 设备已确认，更送进度：100%... 配置更新完成" |
| **focus_metrics** | 完整性、流程正确性 |
| **evaluation_criteria** | 1) detail_id 各轮一致<br>2) step=100 且 fail 为空<br>3) Agent 实时播报进度 |
| **reference** | TC-LIFE-003 |

#### E2E-006: 获取设备配置文件（需设备模拟）

| 字段 | 内容 |
|------|------|
| case_id | E2E-006 |
| case_name | 获取设备配置文件 |
| category_level1 | OpenClaw E2E |
| category_level2 | 生命周期 |
| mode | 2轮 |
| **question** | "帮我获取 cpe-sn-001 的配置文件" |
| **steps** | 1. Agent 理解用户意图，下发获取文件请求<br>2. Agent 订阅 profile/download/process，等待设备返回<br>3. 模拟设备发布结果（download_url 或 fail）<br>4. Agent 告知用户文件获取结果 |
| **expected_answer** | "已获取 cpe-sn-001 的配置文件，下载地址：https://..." 或 "获取失败，设备返回错误：xxx" |
| **focus_metrics** | 正确性 |
| **evaluation_criteria** | 1) detail_id 匹配<br>2) download_url 非空或 fail 非空<br>3) Agent 返回用户友好的结果描述 |
| **reference** | TC-LIFE-004 |

### 13.3 E2E 测试用例快速索引

| Case ID | 名称 | 用户输入（question） | 设备模拟 | 对应 TC |
|---------|------|---------------------|---------|---------|
| E2E-001 | 九井云物模型属性上报与查询还原 | "我的设备 sensor-001 刚上报了数据，帮我确认一下有没有存下来？" | 否 | TC-SMOKE-003 |
| E2E-002 | 服务状态检查与设备查询 | "系统现在正常运行吗？有哪些设备连上来了？" | 否 | TC-SMOKE-001/002 |
| E2E-003 | 设备功能下发与回复闭环 | "帮我把 cpe-sn-001 的设备名称改成 TestRouter" | 是 | TC-OPS-002 |
| E2E-004 | OTA 升级全流程 | "对 cpe-sn-001 执行 OTA 升级到版本 1.0.1" | 是 | TC-LIFE-001 |
| E2E-005 | 批量配置下发全流程 | "给 cpe-sn-001 下发批量配置更新" | 是 | TC-LIFE-003 |
| E2E-006 | 获取设备配置文件 | "帮我获取 cpe-sn-001 的配置文件" | 是 | TC-LIFE-004 |
| E2E-006 | 获取设备配置文件 | 是 | [6.jiujing_获取设备配置文件或日志文件.md](../../docs/reference/6.jiujing_获取设备配置文件或日志文件.md) |

---

## 11. 测试用例索引

| Case ID | 名称 | 层级 | 关键词 | 参考文档 |
|---------|------|------|--------|----------|
| TC-SMOKE-001 | 服务健康检查 | 冒烟 | health, mqtt, influxdb | [2.jiujing_mqtt连接.md](../reference/2.jiujing_mqtt连接.md) |
| TC-SMOKE-002 | 设备列表查询 | 冒烟 | devices, list | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-SMOKE-003 | 设备遥测数据查询 | 冒烟 | telemetry | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-CAP-001 | 设备详情查询 | 能力 | device detail | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-CAP-002 | 设备状态查询 | 能力 | status | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-CAP-003 | 时间范围查询 | 能力 | time range | [3.jiujing_物模型属性定义及上报.md](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-CAP-004 | 分页限制 | 能力 | pagination, limit | [tools.md](../../openclaw/iot-mqtt-bridge/references/tools.md) |
| TC-CAP-005 | 不存在的设备查询 | 能力 | error handling | [agent-guidelines.md](../../openclaw/iot-mqtt-bridge/references/agent-guidelines.md) |
| TC-CAP-006 | MQTT 到 InfluxDB 存储验证 | 能力 | end-to-end | [2.jiujing](../reference/2.jiujing_mqtt连接.md), [3.jiujing](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-CAP-007 | Line Protocol 格式验证 | 能力 | data format | [3.jiujing](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-CAP-008 | 批处理 flush 验证 | 能力 | batch, performance | [config.yaml](../../config.yaml) |
| TC-OPS-001 | 修改设备名称 | 运维操作 | SetDeviceName | [4.jiujing](../reference/4.jiujing_设备功能.md) §1 |
| TC-OPS-002 | NTP 配置下发 | 运维操作 | SetNTPConfig | [4.jiujing](../reference/4.jiujing_设备功能.md) §2, [3.jiujing](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-OPS-003 | 设备定时重启 | 运维操作 | DeviceReboot | [4.jiujing](../reference/4.jiujing_设备功能.md) §8, [8.jiujing](../reference/8.jiujing_平台告警触发机制.md) |
| TC-OPS-004 | WAN 优先级调整 | 运维操作 | WANPriority | [4.jiujing](../reference/4.jiujing_设备功能.md) §12 |
| TC-OPS-005 | 移动网络配置 | 运维操作 | MobileNetworkConfig | [4.jiujing](../reference/4.jiujing_设备功能.md) §14, [3.jiujing](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-OPS-006 | SIM 卡切换 | 运维操作 | SIMConfig | [4.jiujing](../reference/4.jiujing_设备功能.md) §19, [3.jiujing](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-OPS-007 | 双机热备配置 | 运维操作 | HotStandby | [4.jiujing](../reference/4.jiujing_设备功能.md) §20 |
| TC-OPS-008 | VLAN 配置 | 运维操作 | VLANConfig | [4.jiujing](../reference/4.jiujing_设备功能.md) §21 |
| TC-LIFE-001 | OTA 升级全流程 | 生命周期 | OTA, upgrade, process | [5.jiujing](../reference/5.jiujing_ota升级.md) |
| TC-LIFE-002 | OTA 升级拒绝 | 生命周期 | OTA, fail | [5.jiujing](../reference/5.jiujing_ota升级.md) |
| TC-LIFE-003 | 批量配置下发 | 生命周期 | profile, config | [7.jiujing](../reference/7.jiujing_批量配置和设备配置更新.md) |
| TC-LIFE-004 | 获取设备配置文件 | 生命周期 | download, profile | [6.jiujing](../reference/6.jiujing_获取设备配置文件或日志文件.md) |
| TC-LIFE-005 | 获取设备日志文件 | 生命周期 | download, log | [6.jiujing](../reference/6.jiujing_获取设备配置文件或日志文件.md) |
| TC-PROP-001 | 完整物模型属性上报 | 物模型 | jiujing format, 30+ fields | [3.jiujing](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-PROP-002 | 嵌套结构属性解析 | 物模型 | nested JSON, SIMCard, MobileNetwork | [3.jiujing](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-PROP-003 | PING 结果单独上报 | 物模型 | PINGResult, array | [3.jiujing](../reference/3.jiujing_物模型属性定义及上报.md) |
| TC-ADV-001 | 非法时间参数 | 对抗 | invalid input | [tools.md](../../openclaw/iot-mqtt-bridge/references/tools.md) |
| TC-ADV-002 | SQL 注入防护 | 对抗 | security | [SKILL.md](../../openclaw/iot-mqtt-bridge/SKILL.md) |
| TC-ADV-003 | 超大 limit 参数 | 对抗 | boundary | [tools.md](../../openclaw/iot-mqtt-bridge/references/tools.md) |
| TC-ADV-004 | MQTT QoS 级别处理 | 对抗 | QoS | [config.yaml](../../config.yaml), [2.jiujing](../reference/2.jiujing_mqtt连接.md) |
| TC-ADV-005 | 快速批量消息压力测试 | 对抗 | stress | [config.yaml](../../config.yaml) |
| TC-ADV-006 | 设备功能回复超时 | 对抗 | ops timeout | [4.jiujing](../reference/4.jiujing_设备功能.md), [8.jiujing](../reference/8.jiujing_平台告警触发机制.md) |
| TC-ADV-007 | 设备回复错误码 | 对抗 | ops error code | [4.jiujing](../reference/4.jiujing_设备功能.md) |
| TC-ADV-008 | 无效功能命令 serviceName | 对抗 | invalid serviceName | [4.jiujing](../reference/4.jiujing_设备功能.md), [2.jiujing](../reference/2.jiujing_mqtt连接.md) |

---

## 12. 修改历史

| 日期 | 版本 | 修改内容 |
|------|------|----------|
| 2026-05-09 | 1.0.0 | 初始版本，创建测试用例 16 个 |
| 2026-05-11 | 2.0.0 | 增强版本：新增运维操作层8个、生命周期层5个、物模型层3个、对抗层3个，总计35个；添加九井云参考文档链接；添加告警关联索引 |
