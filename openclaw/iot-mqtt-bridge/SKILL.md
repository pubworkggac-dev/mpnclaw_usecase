---
name: iot-mqtt-bridge
description: 通过 bridge HTTP API 查询 IoT 设备数据（设备列表、历史遥测、最新状态）。当用户询问设备是否在线、某设备最近一段时间数据、或最新状态时使用。
---

# iot-mqtt-bridge

用于查询 MQTT -> Bridge -> InfluxDB v2 链路中的设备数据。

## 适用任务

- 查询设备列表
- 查询设备历史遥测（时间范围 + 条数限制）
- 查询设备最新状态
- 快速健康检查（bridge / mqtt / influxdb）
- **下发控制命令到九井云设备**（如修改配置、重启设备等）

## 非目标

- 不负责部署/启动 InfluxDB、MQTT、Bridge
- 不负责修复服务故障
- 不提供 InfluxDB v2 下的 raw SQL 能力（`query_sql` 仅兼容保留）

## 前置条件

1. Bridge 服务可访问（默认 `http://localhost:8080`）
2. `scripts/adapter.sh` 可执行
3. 如需覆盖地址：`OPENCLAW_ADAPTER_BASE_URL=http://<host>:<port>`

## 工具列表

| 工具 | 说明 |
|------|------|
| `query_devices` | 查询设备列表 |
| `query_device_telemetry` | 查询设备历史遥测 |
| `query_device_status` | 查询设备最新状态 |
| `query_sql` | 兼容保留的 SQL 查询 |
| `send_command` | 下发设备命令（同步响应模式） |

详细参数说明见 `references/tools.md`。

## 设备命令下发 (send_command)

Bridge 通过 WebSocket 直连 Gateway，收到 MQTT 设备 reply 后主动推送结果到 Agent session。

### 触发词
- "下发设备命令"
- "发送命令到设备"
- "执行设备命令"

### 输入参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| product_key | string | 是 | 产品标识 |
| device_key | string | 是 | 设备标识 |
| service_name | string | 是 | 服务名称，如 SetDeviceName |
| params | object | 是 | 命令参数字典 |
| session_key | string | 否 | OpenClaw 会话标识，不传则使用 Bridge 配置的默认值 |

### 输出
```json
{
  "success": true,
  "message_id": "uuid-xxx",
  "topic": "/system/pk/dk/thing/service/SetDeviceName",
  "payload": "{...}",
  "session_key": "agent:main:main"
}
```

### 命令状态查询
GET /api/v1/commands/{message_id}/status

### 工作原理
1. Agent 调用 send_command（**必须传自己的 session_key**）→ Bridge 发布 MQTT 命令到设备
2. Bridge 本地存储命令状态（_commands_map），启动超时检测
3. 设备执行命令，发布响应到 _reply topic
4. Bridge MQTT 收到响应，更新本地状态，通过 WebSocket 调用 `sessions.send` 推送到指定 session_key 对应的 Agent session
5. Agent 可通过 `GET /api/v1/commands/{message_id}/status` 查询命令执行结果（从本地读取）
6. Agent 应通过 `openclaw sessions --json` 获取自己的 sessionKey 传入，确保推送通知到达正确的会话

### 九井云服务列表
- SetDeviceName, DeviceReboot, WANPriority, LANConfig
- 更多服务见 src/models/command.py: JIUJINGYUN_SERVICES
