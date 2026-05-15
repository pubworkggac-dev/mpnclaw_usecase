# MQTT-InfluxDB 脚本目录

## 目录结构

```
scripts/
├── run.sh              # 总入口（一键启动/安装/测试）
├── env_common.sh       # 公共环境变量
│
├── install/            # 安装脚本
│   ├── install.sh      # 一键安装入口
│   ├── install_docker.sh
│   ├── install_native.sh
│   ├── influxdb_install_*.sh
│   ├── nanomq_install_*.sh
│   ├── mosquitto_install_*.sh
│   ├── docker-compose.nanomq.yml
│   └── docker-compose.mosquitto.yml
│
├── init/               # 初始化脚本
│   └── influxdb_v2.sh  # 初始化 InfluxDB v2
│
├── start/              # 启动脚本
│   ├── influxdb.sh     # InfluxDB（本机）
│   ├── influxdb_docker.sh
│   ├── nanomq.sh
│   ├── mosquitto.sh
│   └── bridge.sh       # 桥接服务
│
└── test/               # 测试脚本
    └── smoke.sh       # 冒烟测试
```

## 快速使用

```bash
cd usecase/1.mqtt_influxdb
bash scripts/run.sh help
```

## 命令说明

| 命令 | 说明 |
|------|------|
| `bash scripts/run.sh install` | 一键安装 |
| `bash scripts/run.sh init` | 初始化 InfluxDB |
| `bash scripts/run.sh start` | 显示启动指南 |
| `bash scripts/run.sh stop` | 停止所有 Docker 容器 |
| `bash scripts/run.sh test` | 运行冒烟测试 |

## 手动操作

### 安装

```bash
# 一键安装
bash scripts/install/install.sh

# 单独安装组件
bash scripts/install/influxdb_install_native.sh
bash scripts/install/nanomq_install_native.sh
```

### 启动顺序

1. **InfluxDB**（终端 1）
   ```bash
   bash scripts/start/influxdb.sh        # 本机
   # 或
   bash scripts/start/influxdb_docker.sh  # Docker
   ```

2. **MQTT Broker**（终端 2，二选一）
   ```bash
   bash scripts/start/nanomq.sh           # nanoMQ
   # 或
   bash scripts/start/mosquitto.sh         # Mosquitto
   ```

3. **桥接服务**（终端 3）
   ```bash
   bash scripts/start/bridge.sh
   ```

4. **冒烟测试**（终端 4）
   ```bash
   bash scripts/test/smoke.sh
   ```

## Docker Compose 启动

```bash
# InfluxDB + nanoMQ
docker compose -f scripts/install/docker-compose.nanomq.yml up

# InfluxDB + Mosquitto
docker compose -f scripts/install/docker-compose.mosquitto.yml up
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `INSTALL_DIR` | `.local` | 自定义安装目录 |
| `INFLUXDB_NATIVE_BIN` | 自动探测 | influxd 路径 |
| `NANOMQ_BIN` | 自动探测 | nanomq 路径 |
| `NANOMQ_TCP_PORT` | `1883` | nanoMQ 端口 |
| `MQTT_HOST` | `localhost` | MQTT 主机 |
| `MQTT_PORT` | `1883` | MQTT 端口 |
| `SKIP_UV_SYNC` | `0` | 跳过 uv sync |