# Flux 查询示例（influxdb-query）

## 基础查询

### 最近1小时所有数据
```flux
from(bucket: "iot_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
```

### 特定设备最近数据
```flux
from(bucket: "iot_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> filter(fn: (r) => r.device_id == "device-001")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 100)
```

## 过滤条件

### 按传感器类型
```flux
from(bucket: "iot_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> filter(fn: (r) => r.sensor_type == "temperature")
```

### 多条件过滤
```flux
from(bucket: "iot_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> filter(fn: (r) => r.device_id == "device-001")
  |> filter(fn: (r) => r.sensor_type == "temperature")
  |> filter(fn: (r) => r.value > 25.0)
```

### 按位置过滤
```flux
from(bucket: "iot_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> filter(fn: (r) => r.location == "building-a")
```

## 聚合统计

### 每小时平均值
```flux
from(bucket: "iot_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> filter(fn: (r) => r.device_id == "device-001")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> group(columns: ["sensor_type"])
```

### 每小时最大值最小值
```flux
from(bucket: "iot_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> filter(fn: (r) => r.device_id == "device-001")
  |> aggregateWindow(every: 1h, fn: max, createEmpty: false)
  |> union(table: that(
    from(bucket: "iot_data")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "device_telemetry")
      |> filter(fn: (r) => r.device_id == "device-001")
      |> aggregateWindow(every: 1h, fn: min, createEmpty: false)
  ))
```

### 设备在线时长统计
```flux
from(bucket: "iot_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> group(columns: ["device_id"])
  |> reduce(
    identity: {count: 0, first_time: now(), last_time: now()},
    fn: (r, accumulator) => ({
      count: accumulator.count + 1.0,
      first_time: if accumulator.count == 0.0 then r._time else accumulator.first_time,
      last_time: r._time
    })
  )
```

## 时间范围

| 表达式 | 说明 |
|--------|------|
| `-1h` | 最近1小时 |
| `-24h` | 最近24小时 |
| `-7d` | 最近7天 |
| `-30d` | 最近30天 |
| `2024-01-01T00:00:00Z` | 绝对时间 |
| `start: -1d, stop: now()` | 范围写法 |