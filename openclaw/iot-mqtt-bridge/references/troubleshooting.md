# 故障排查指南（iot-mqtt-bridge）

## 快速诊断流程

```
1. 检查 Bridge 服务是否运行
   curl http://localhost:6601/health

2. 若 health 失败 → 检查服务状态 / 端口连通性
3. 若 health 成功但 API 失败 → 检查具体接口
4. 若数据缺失 → 检查 MQTT 连接 / InfluxDB 连接
```

## 常见问题

### 1. Health 检查失败

**症状**：`curl` 无响应或连接被拒绝

**排查步骤**：
```bash
# 1. 检查服务进程是否存活
ps aux | grep "python -m src.main" | grep -v grep

# 2. 检查端口是否监听
netstat -tlnp | grep 6601   # Linux
ss -tlnp | grep 6601        # Linux (modern)
netstat -ano | findstr 6601 # Windows

# 3. 检查服务日志
# 查看启动脚本输出或 journalctl
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| 服务未启动 | `uv run python -m src.main` |
| 端口被占用 | 杀掉占用进程或改用其他端口 |
| 防火墙阻断 | 检查本地防火墙规则 |
| 配置错误 | 检查 `config.yaml` 中 `http.port` |

---

### 2. MQTT 连接失败

**症状**：`health` 返回 `"mqtt_connected": false`

**排查步骤**：
```bash
# 1. 检查 MQTT Broker 是否运行
netstat -tlnp | grep 1883

# 2. 测试 MQTT 连接
mosquitto_pub -h localhost -p 1883 -t "test" -m "ping"
mosquitto_sub -h localhost -p 1883 -t "test" -C 1

# 3. 检查配置中的 broker 地址
# config.yaml 中的 mqtt.broker 是否正确
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| Broker 未启动 | 启动 Mosquitto/nanoMQ |
| Broker 地址错误 | 修改 `config.yaml` 中 `mqtt.broker` |
| 认证失败 | 检查 `mqtt.username` / `mqtt.password` |
| 防火墙阻断 | 检查 1883 端口 |

---

### 3. InfluxDB 连接失败

**症状**：`health` 返回 `"influxdb_connected": false`

**排查步骤**：
```bash
# 1. 检查 InfluxDB 是否运行
curl -s http://localhost:8086/health

# 2. 检查 Token 是否有效
curl -s -H "Authorization: Token ${INFLUXDB_TOKEN}" \
  http://localhost:8086/api/v2/buckets | jq .buckets

# 3. 检查 Bucket 是否存在
# 默认 bucket: iot_data
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| InfluxDB 未启动 | 启动 InfluxDB v2 (`influxd`) |
| Token 错误 | 检查 `config.yaml` 中 `influxdb.token` |
| Bucket 不存在 | 执行初始化脚本创建 bucket |
| 网络不通 | 检查 `influxdb.url` 地址 |

---

### 4. 查询设备无数据

**症状**：`query_devices` 返回空数组或 `query_device_telemetry` 无数据

**排查步骤**：
```bash
# 1. 先 health 检查整体状态

# 2. 确认设备 ID 拼写正确
curl http://localhost:6601/api/v1/devices

# 3. 检查时间范围是否正确
# 默认 start=-1h，检查设备是否在最近 1 小时有数据

# 4. 直接查询 InfluxDB 验证数据存在
# 使用 influxdb-query skill 直接查询
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| 设备未上报数据 | 检查设备 MQTT 连接 |
| 时间范围错误 | 扩大 start 参数（如 `-24h`） |
| device_id 拼写错误 | 核对设备 ID 大小写 |
| 数据未写入 InfluxDB | 检查 Bridge 日志 |

---

### 5. 命令下发失败

**症状**：`send_command` 返回 MQTT 发布失败

**排查步骤**：
```bash
# 1. 检查 MQTT 连接状态（必须先 MQTT connected 才能发命令）
curl http://localhost:6601/health | jq .mqtt_connected

# 2. 检查 product_key / device_key 是否正确
# 这些需要从九井云平台获取

# 3. 检查服务名称是否支持
# 参考 jiujingyun-protocol.md 中的服务列表

# 4. 查看 Bridge 日志中的详细错误
```

**可能原因**：
| 原因 | 解决方案 |
|------|----------|
| MQTT 未连接 | 先确保 MQTT connected |
| 设备不存在 | 核对 product_key / device_key |
| 服务名错误 | 参考协议文档 |
| 参数格式错误 | 检查 JSON 参数格式 |

---

### 6. HTTP 响应错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| 200 | 成功 | - |
| 400 | 请求参数错误 | 检查参数格式 |
| 404 | 设备不存在 | 检查 device_id |
| 500 | 服务器内部错误 | 查看服务日志 |
| 503 | 服务不可用（如InfluxDB未连接） | 检查依赖服务状态 |

---

## 环境变量速查

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLAW_ADAPTER_BASE_URL` | `http://localhost:6601` | Bridge 服务地址 |
| `MQTT_BROKER` | `tcp://localhost:1883` | MQTT Broker 地址 |
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB 地址 |
| `INFLUXDB_TOKEN` | - | InfluxDB 认证 Token |
| `CONFIG_PATH` | `config.yaml` | 配置文件路径 |

---

## 日志位置

Bridge 服务默认输出到 stdout，日志格式为 JSON。  
可通过 `scripts/start_bridge.sh` 重定向到文件：

```bash
uv run python -m src.main > logs/bridge.log 2>&1
```

日志级别可通过 `config.yaml` 的 `logging.level` 调整（DEBUG/INFO/WARNING/ERROR）。