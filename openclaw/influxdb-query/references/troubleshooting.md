# 故障排查指南（influxdb-query）

## 快速诊断流程

```
1. 检查 InfluxDB 服务是否运行
   curl http://localhost:8086/health

2. 若 health 失败 → 检查 InfluxDB 进程 / 端口连通性
3. 若 health 成功但查询失败 → 检查 Token / Bucket 名称
4. 若查询慢 → 检查时间范围和数据量
```

## 常见问题

### 1. Health 检查失败

**症状**：`curl http://localhost:8086/health` 无响应或 404

**排查步骤**：
```bash
# 1. 检查 InfluxDB 进程是否运行
ps aux | grep influxd | grep -v grep

# 2. 检查端口是否监听
netstat -tlnp | grep 8086   # Linux
ss -tlnp | grep 8086        # Linux (modern)
netstat -ano | findstr 8086  # Windows

# 3. 查看 InfluxDB 日志
# 默认日志位置: $HOME/.influxdbv2/logs/
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| InfluxDB 未启动 | `influxd` 或 `scripts/start_influxdb_native.sh` |
| 端口配置错误 | 检查是否有其他服务占用 8086 |
| 版本不兼容 | 确认使用 InfluxDB v2（v1.x 使用不同 API） |

---

### 2. Token 认证失败

**症状**：`curl` 返回 401 Unauthorized 或 403 Forbidden

**排查步骤**：
```bash
# 1. 检查 Token 是否设置
echo $INFLUXDB_TOKEN

# 2. 验证 Token 有效性
curl -s -H "Authorization: Token ${INFLUXDB_TOKEN}" \
  http://localhost:8086/api/v2/buckets | jq .

# 3. 获取新 Token（如果失效）
# 访问 InfluxDB Web UI (http://localhost:8086) → Settings → Tokens
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| Token 未设置 | `export INFLUXDB_TOKEN=your-token` |
| Token 过期 | 到 InfluxDB UI 重新生成 |
| Token 权限不足 | 确保 Token 有读 bucket 权限 |

---

### 3. Bucket 不存在

**症状**：查询返回 "bucket not found" 或空数据

**排查步骤**：
```bash
# 1. 列出所有 Bucket
scripts/flux_query.sh list_buckets

# 2. 检查默认 bucket 名称
# 默认: iot_data (可通过 INFLUXDB_DATABASE 覆盖)

# 3. 创建缺失的 Bucket
influx bucket create -n iot_data -o my-org
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| Bucket 未创建 | 执行初始化脚本 |
| Bucket 名称拼写错误 | 检查 `INFLUXDB_DATABASE` 配置 |
| 使用了错误的 Organization | 检查 `INFLUXDB_ORG` |

---

### 4. 查询返回空数据

**症状**：Flux 查询返回 `[]` 但确认有数据

**排查步骤**：
```bash
# 1. 检查时间范围是否包含数据
# 使用绝对时间测试:
scripts/flux_query.sh 'from(bucket: "iot_data") |> range(start: -24h) |> limit(n: 10)'

# 2. 检查 measurement 名称
# 确认使用正确的 measurement 名 (device_telemetry)

# 3. 检查 tag/field 名称大小写
# InfluxDB 区分大小写
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| 时间范围不包含数据 | 扩大 range 的 start 值 |
| 大小写不匹配 | 检查 device_id、sensor_type 等大小写 |
| 过滤条件错误 | 移除 filter 测试基础查询 |

---

### 5. 查询超时或太慢

**症状**：查询长时间无响应或超时

**排查步骤**：
```bash
# 1. 减小时间范围测试
# 从最近 1 小时数据开始，避免大范围查询

# 2. 添加 limit 限制返回行数
|> limit(n: 1000)

# 3. 检查是否有复杂聚合
# 尝试简化查询逐步排查

# 4. 检查 InfluxDB 资源
# CPU/内存/磁盘是否瓶颈
```

**优化建议**：
| 问题 | 解决方案 |
|------|----------|
| 数据量太大 | 使用 aggregateWindow 降采样 |
| 查询太频繁 | 增加查询间隔 |
| 全表扫描 | 添加更精确的 filter |

---

## 环境变量速查

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB 服务地址 |
| `INFLUXDB_TOKEN` | - | 认证 Token（必填） |
| `INFLUXDB_ORG` | `my-org` | Organization 名称 |
| `INFLUXDB_DATABASE` | `iot_data` | 默认 Bucket 名称 |

---

## 常用诊断命令

```bash
# 检查服务健康
scripts/flux_query.sh health

# 列出所有 Bucket
scripts/flux_query.sh list_buckets

# 列出所有 Measurement
scripts/flux_query.sh list_measurements

# 查看最近 10 条数据
scripts/flux_query.sh 'from(bucket: "iot_data") |> range(start: -1h) |> limit(n: 10)'

# 检查 Token 是否有效
curl -s -H "Authorization: Token ${INFLUXDB_TOKEN}" \
  http://localhost:8086/api/v2/me | jq .
```

---

## HTTP 错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| 200 | 查询成功 | - |
| 400 | 查询语法错误 | 检查 Flux 语法 |
| 401 | Token 无效或缺失 | 检查 INFLUXDB_TOKEN |
| 403 | Token 权限不足 | 确保有读权限 |
| 404 | Bucket/Resource 不存在 | 检查 Bucket 名称 |
| 500 | InfluxDB 内部错误 | 查看 InfluxDB 日志 |
| 599 | 连接超时 | 检查网络和服务状态 |