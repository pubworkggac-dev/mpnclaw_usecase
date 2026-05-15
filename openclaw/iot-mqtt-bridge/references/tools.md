# Tools（iot-mqtt-bridge）

默认服务地址：

```bash
export OPENCLAW_ADAPTER_BASE_URL=http://localhost:6601
```

## health

- 参数：无
- 用途：查询 bridge 健康状态（含 mqtt/influxdb 连接状态）
- 命令：`scripts/adapter.sh health`
- 返回：JSON 对象

**成功响应示例**：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "mqtt_connected": true,
  "influxdb_connected": true
}
```

**故障响应示例**：
```json
{
  "status": "unhealthy",
  "mqtt_connected": false,
  "influxdb_connected": true,
  "error": "MQTT broker connection lost"
}
```

**判断标准**：
- `"status": "healthy"` 且 `mqtt_connected: true` 且 `influxdb_connected: true` → 服务正常
- `mqtt_connected: false` → MQTT 连接断开，需检查 Broker
- `influxdb_connected: false` → InfluxDB 连接断开，需检查 InfluxDB 状态

## query_devices

- 参数：无
- 用途：查询设备列表
- 命令：`scripts/adapter.sh query_devices`
- 返回：JSON `{success, data: [{device_id, ...}], count}`

**成功响应示例**：
```json
{
  "success": true,
  "data": [
    {"device_id": "device-001", "_time": "2026-05-12T10:00:00Z"},
    {"device_id": "device-002", "_time": "2026-05-12T09:55:00Z"}
  ],
  "count": 2
}
```

**失败响应示例**：
```json
{
  "success": false,
  "error": "InfluxDB not available"
}
```

## query_device_telemetry

- 参数：
  - `device_id`（必填）
  - `start`（可选，默认 `-1h`）
  - `end`（可选，默认 `now`）
  - `limit`（可选，默认 `100`，最大 `10000`）
- 用途：查询设备历史遥测
- 命令：`scripts/adapter.sh query_device_telemetry <device_id> [start] [end] [limit]`
- 返回：JSON `{success, device_id, data, meta, error}`

**成功响应示例**：
```json
{
  "success": true,
  "device_id": "device-001",
  "data": [
    {
      "_time": "2026-05-12T10:00:00Z",
      "device_id": "device-001",
      "sensor_type": "temperature",
      "value": 25.5,
      "unit": "celsius",
      "location": "building-a"
    }
  ],
  "meta": {"count": 1, "start": "-1h", "end": "now"}
}
```

**无数据响应示例**：
```json
{
  "success": true,
  "device_id": "device-001",
  "data": [],
  "meta": {"count": 0}
}
```

## query_device_status

- 参数：`device_id`（必填）
- 用途：查询设备最近状态
- 命令：`scripts/adapter.sh query_device_status <device_id>`
- 返回：JSON（结构同 `query_device_telemetry`，但 limit=1）

**成功响应示例**：
```json
{
  "success": true,
  "device_id": "device-001",
  "data": [
    {
      "_time": "2026-05-12T10:00:00Z",
      "device_id": "device-001",
      "sensor_type": "temperature",
      "value": 25.5,
      "unit": "celsius"
    }
  ]
}
```

## query_sql（兼容保留）

- 参数：`sql`（必填）
- 用途：兼容入口，会转发到 `/api/v1/query`
- 说明：在 InfluxDB v2 模式下通常返回"not available"提示
- 命令：`scripts/adapter.sh query_sql '<sql>'`

**响应示例**：
```json
{
  "success": false,
  "error": "InfluxDB not available (mock mode)"
}
```

## send_command

- 参数：
  - `product_key`（必填）- 产品唯一标识
  - `device_key`（必填）- 设备唯一标识
  - `service_name`（必填）- 服务名称，如 `SetDeviceName`、`WANPriority`
  - `params_json`（可选，默认 `{}`）- 命令参数字符串 JSON
  - `session_key`（可选）- OpenClaw 会话标识，不传则使用预设默认值
- 用途：向九井云设备下发控制命令（通过 MQTT），可指定 sessionKey
- 命令：`scripts/adapter.sh send_command <product_key> <device_key> <service_name> [params_json] [session_key]`
- 说明：参见 `references/jiujingyun-protocol.md` 了解支持的命令列表和参数格式

**成功响应示例**：
```json
{
  "success": true,
  "message_id": "msg-123456",
  "detail": "Command published to MQTT"
}
```

**失败响应示例**：
```json
{
  "success": false,
  "detail": "MQTT publish failed: not connected"
}
```

## 错误码对照表

| HTTP 状态码 | 含义 | 可能原因 |
|-------------|------|----------|
| 200 | 请求成功 | - |
| 400 | 参数错误 | 缺少必需参数或格式错误 |
| 404 | 设备不存在 | device_id 拼写错误或设备未注册 |
| 500 | 服务器错误 | Bridge 服务内部异常 |
| 503 | 服务不可用 | MQTT 或 InfluxDB 未连接 |
