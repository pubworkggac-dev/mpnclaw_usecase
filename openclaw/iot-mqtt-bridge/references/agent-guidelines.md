# Agent Guidelines（iot-mqtt-bridge）

## 响应策略

1. 先工具调用再解释，避免臆测
2. 如需判断整体可用性，先调用 `health`
3. 查询不到数据时，给出可执行排查建议

## 输出建议

- 优先展示关键字段：`device_id`、`sensor_type`、`value`、`unit`、`time`
- 多条记录按时间降序（最新优先）
- 明确区分“无数据”和“服务故障”

## v2 约束

- InfluxDB v2 模式下，不承诺 raw SQL 查询能力
- 当用户要求 SQL 时，优先引导使用设备/遥测接口

## 命令下发指南

1. **确认设备标识**：需要 `product_key` 和 `device_key`（从九井云平台获取）
2. **选择服务名称**：参考 `jiujingyun-protocol.md` 的服务列表
3. **构造参数**：查看对应服务的参数格式（如 `{"DeviceName":"MyRouter"}`）
4. **传入 session_key**：**必须**传自己的 sessionKey（可通过 `openclaw sessions --json` 获取），否则 Bridge 会使用默认值推送到错误的 session。示例：`send_command ... session_key="agent:ueg-superclaw:main"`
5. **调用 send_command**：参数以 JSON 字符串传入
6. **解析响应**：成功时 `code=200`，失败时 `code!=200` 且有 `fail` 字段

### 常用命令示例

```bash
# 重启设备（传入当前 Agent 的 session_key）
send_command test-product test-device-001 RebootDevice '{}' 'agent:ueg-superclaw:main'

# 修改设备名称
send_command test-product test-device-001 SetDeviceName '{"DeviceName":"OfficeRouter"}' 'agent:ueg-superclaw:main'

# WAN优先级配置
send_command test-product test-device-001 WANPriority '{"Interface":"nrWan","Priority":1}' 'agent:ueg-superclaw:main'
```

### 响应判断

- **成功**：`{"success":true, "message_id":"..."}` 表示命令已发送
- **MQTT错误**：`{"success":false, "detail":"MQTT publish failed"}` 表示发布失败
- **设备回复**：设备会在 `_reply` topic 回复，查看 `jiujingyun-protocol.md` 的回复格式
