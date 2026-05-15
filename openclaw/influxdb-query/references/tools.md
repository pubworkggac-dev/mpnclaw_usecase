# Tools（influxdb-query）

环境变量：
```bash
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=your-token-here
export INFLUXDB_ORG=my-org
export INFLUXDB_DATABASE=iot_data
```

## flux_query

- 参数：
  - `flux`（必填）- Flux 查询语句
  - `database`（可选，默认 `iot_data`）- bucket 名称
- 用途：执行任意 Flux 查询
- 命令：`scripts/flux_query.sh '<flux_query>' [database]`
- 返回：JSON `{success, data, meta, error}`

**成功响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "_time": "2026-05-12T10:00:00Z",
      "device_id": "device-001",
      "sensor_type": "temperature",
      "value": 25.5,
      "unit": "celsius"
    }
  ],
  "meta": {"count": 1}
}
```

**失败响应示例**：
```json
{
  "success": false,
  "error": "HTTP 401",
  "data": []
}
```

## health

- 参数：无
- 用途：检查 InfluxDB 服务可达性
- 命令：`scripts/flux_query.sh health`
- 返回：HTTP 状态码字符串（如 `200`、`401`、`unreachable`）

**返回码说明**：
| 返回值 | 含义 |
|--------|------|
| `200` | InfluxDB 服务正常 |
| `401` | Token 无效或缺失 |
| `unreachable` | 服务不可达（网络问题或服务未启动）|

**使用建议**：
```bash
# 检查 health 并判断是否成功
code=$(scripts/flux_query.sh health)
if [ "$code" = "200" ]; then
  echo "InfluxDB OK"
else
  echo "InfluxDB 问题: $code"
fi
```

## list_buckets

- 参数：无
- 用途：列出 InfluxDB 中的所有 bucket
- 命令：`scripts/flux_query.sh list_buckets`
- 返回：bucket 名称列表（每行一个）

**响应示例**：
```
iot_data
telegraf
_meta
```

## list_measurements

- 参数：
  - `database`（可选，默认 `iot_data`）
- 用途：列出指定 bucket 中的 measurement
- 命令：`scripts/flux_query.sh list_measurements [database]`
- 返回：JSON 数组

**成功响应示例**：
```json
["device_telemetry", "system_metrics"]
```

## 错误处理指南

| 错误类型 | 特征 | 解决方案 |
|----------|------|----------|
| Token 无效 | `success: false, error: "HTTP 401"` | 检查 INFLUXDB_TOKEN 是否正确 |
| Bucket 不存在 | `success: false, error: "bucket not found"` | 检查 bucket 名称是否正确 |
| 查询超时 | 无响应或超时 | 减小查询范围或添加 limit |
| 服务不可达 | `error: "HTTP unreachable"` | 检查 InfluxDB 是否启动 |