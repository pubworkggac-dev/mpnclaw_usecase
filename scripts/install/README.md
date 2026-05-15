# MQTT-InfluxDB 安装脚本

## 目录结构

```
install/
├── README.md                    # 本文件
├── install.sh                   # 总一键安装入口
├── install_docker.sh            # Docker 完整安装
├── install_native.sh            # 本机完整安装
├── influxdb_install_native.sh
├── influxdb_install_docker.sh
├── nanomq_install_native.sh
├── nanomq_install_docker.sh
├── mosquitto_install_native.sh
├── mosquitto_install_docker.sh
├── docker-compose.nanomq.yml     # Docker: InfluxDB + nanoMQ
└── docker-compose.mosquitto.yml # Docker: InfluxDB + Mosquitto
```

## 快速开始

### 一键安装（推荐）

```bash
cd usecase/1.mqtt_influxdb
bash scripts/install/install.sh
```

脚本会自动：
1. 检测当前操作系统（macOS / Windows / Linux）
2. 检测 Docker 是否可用
3. 询问安装方式（DOCKER / 本机）
4. 选择要安装的组件
5. MQTT Broker 二选一（nanoMQ 或 Mosquitto）

### Docker Compose 一键启动

**二选一：**

```bash
# 方案 A: InfluxDB + nanoMQ
cd scripts/install
docker compose -f docker-compose.nanomq.yml up

# 方案 B: InfluxDB + Mosquitto
cd scripts/install
docker compose -f docker-compose.mosquitto.yml up
```

停止：

```bash
docker compose -f docker-compose.nanomq.yml down
docker compose -f docker-compose.mosquitto.yml down
```

### 单组件安装

```bash
# InfluxDB
bash scripts/install/influxdb_install_native.sh
bash scripts/install/influxdb_install_docker.sh

# nanoMQ
bash scripts/install/nanomq_install_native.sh
bash scripts/install/nanomq_install_docker.sh

# Mosquitto
bash scripts/install/mosquitto_install_native.sh
bash scripts/install/mosquitto_install_docker.sh
```

## MQTT Broker 选择

nanoMQ 和 Mosquitto 是**二选一**的关系，不能同时使用：

| Broker | 特点 | 端口 |
|--------|------|------|
| nanoMQ | 轻量级，高性能，支持 WebSocket | 1883/8081/8084 |
| Mosquitto | 成熟稳定，广泛使用 | 1883 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `INFLUXDB_IMAGE` | `influxdb:2` | InfluxDB 镜像 |
| `INFLUXDB_HTTP_PORT` | `8086` | InfluxDB 端口 |
| `NANOMQ_IMAGE` | `emqx/nanomq:0.24.13` | nanoMQ 镜像 |
| `NANOMQ_TCP_PORT` | `1883` | nanoMQ TCP 端口 |
| `MOSQUITTO_IMAGE` | `eclipse-mosquitto:2` | Mosquitto 镜像 |
| `MOSQUITTO_PORT` | `1883` | Mosquitto 端口 |
| `INFLUXDB_INIT_USER` | `admin` | InfluxDB 初始用户 |
| `INFLUXDB_INIT_PASS` | `admin123456` | InfluxDB 初始密码 |
| `INFLUXDB_INIT_ORG` | `my-org` | InfluxDB 组织 |
| `INFLUXDB_INIT_BUCKET` | `iot_data` | InfluxDB bucket |
| `INFLUXDB_INIT_TOKEN` | `my-super-token` | InfluxDB Token |

示例：

```bash
# 使用 nanoMQ，自定义端口
NANOMQ_TCP_PORT=1884 docker compose -f docker-compose.nanomq.yml up
```

## 安装后验证

1. 检查容器状态：
   ```bash
   docker ps
   ```

2. 初始化 InfluxDB（仅首次）：
   ```bash
   bash scripts/init_influxdb_v2.sh
   ```

3. 启动桥接服务：
   ```bash
   bash scripts/start_bridge.sh
   ```

4. 运行冒烟测试：
   ```bash
   bash scripts/run_smoke_test.sh
   ```