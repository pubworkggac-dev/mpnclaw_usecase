# 数据模型（influxdb-query）

## Bucket: `iot_data`（默认）

## Measurement: `device_telemetry`

设备遥测数据，结构如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| device_id | string | 设备唯一标识 |
| sensor_type | string | 传感器类型（如 temperature, humidity） |
| location | string | 设备位置（可选） |
| value | float | 测量值 |
| unit | string | 单位（如 celsius, %） |
| _time | timestamp | 时间戳（InfluxDB 内置） |

## 查询示例

### 设备列表
```flux
from(bucket: "iot_data")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> keep(columns: ["device_id"])
  |> group()
  |> distinct(column: "device_id")
  |> sort(columns: ["device_id"])
```

### 设备遥测（最近1小时）
```flux
from(bucket: "iot_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> filter(fn: (r) => r.device_id == "test-device-001")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 100)
```

### 按传感器类型聚合
```flux
from(bucket: "iot_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> filter(fn: (r) => r.sensor_type == "temperature")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> group(columns: ["device_id"])
  |> sort(columns: ["_time"], desc: true)
```