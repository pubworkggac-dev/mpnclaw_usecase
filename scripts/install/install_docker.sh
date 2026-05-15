#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SCRIPTS_DIR="$SCRIPT_DIR"

echo "=== MQTT-InfluxDB Docker 完整安装 ==="

if ! command -v docker >/dev/null 2>&1; then
  echo "错误: 未找到 docker 命令，请先安装 Docker Desktop。"
  exit 1
fi

echo "检测到 Docker 版本:"
docker --version

COMPOSE_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
  if ! command -v docker-compose >/dev/null 2>&1; then
    echo "错误: 未找到 docker compose 或 docker-compose，请升级 Docker Desktop。"
    exit 1
  fi
fi
echo "使用: $COMPOSE_CMD"

echo ""
echo "请选择要安装的组件:"
echo "  1. InfluxDB (端口 8086)"
echo "  2. MQTT Broker (二选一: nanoMQ 或 Mosquitto，端口 1883)"
echo "  3. 全部组件"
echo ""
echo "默认: 3"
read -r choice
choice="${choice:-3}"

install_influxdb=false
install_broker=false
mqtt_choice="nanomq"

case "$choice" in
  1)
    install_influxdb=true
    ;;
  2)
    install_broker=true
    ;;
  3)
    install_influxdb=true
    install_broker=true
    ;;
esac

if $install_broker; then
  echo ""
  echo "请选择 MQTT Broker (1 = nanoMQ, 2 = Mosquitto，默认: 1):"
  read -r mqtt_choice
  mqtt_choice="${mqtt_choice:-1}"
fi

mkdir -p "$SCRIPT_DIR/../../.local/influxdb2"
mkdir -p "$SCRIPT_DIR/../../.local/nanomq"
mkdir -p "$SCRIPT_DIR/../../.local/mosquitto/config"
mkdir -p "$SCRIPT_DIR/../../.local/mosquitto/data"
mkdir -p "$SCRIPT_DIR/../../.local/mosquitto/log"

if [ ! -f "$SCRIPT_DIR/../../.local/mosquitto/config/mosquitto.conf" ]; then
  cat > "$SCRIPT_DIR/../../.local/mosquitto/config/mosquitto.conf" <<'EOF'
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest stdout
EOF
fi

echo ""
echo "开始安装..."

cd "$SCRIPT_DIR"

if $install_influxdb; then
  echo ""
  echo "[1/2] 启动 InfluxDB..."
  INFLUXDB_IMAGE="${INFLUXDB_IMAGE:-influxdb:2}" \
  INFLUXDB_HTTP_PORT="${INFLUXDB_HTTP_PORT:-8086}" \
  $COMPOSE_CMD -f docker-compose.influxdb2.yml up -d
  echo "InfluxDB 启动完成: http://localhost:8086"
fi

if $install_broker; then
  echo ""
  echo "[2/2] 启动 MQTT Broker..."

  case "$mqtt_choice" in
    1|nanomq)
      echo "启动 nanoMQ..."
      NANOMQ_IMAGE="${NANOMQ_IMAGE:-emqx/nanomq:0.24.13}" \
      NANOMQ_TCP_PORT="${NANOMQ_TCP_PORT:-1883}" \
      NANOMQ_HTTP_PORT="${NANOMQ_HTTP_PORT:-8081}" \
      docker run -d \
        --name nanomq \
        -p "$NANOMQ_TCP_PORT:1883" \
        -p "$NANOMQ_HTTP_PORT:8081" \
        -v "$SCRIPT_DIR/../../.local/nanomq:/etc/nanomq" \
        "$NANOMQ_IMAGE"
      echo "nanoMQ 启动完成: tcp://localhost:$NANOMQ_TCP_PORT"
      ;;

    2|mosquitto)
      echo "启动 Mosquitto..."
      MOSQUITTO_IMAGE="${MOSQUITTO_IMAGE:-eclipse-mosquitto:2}" \
      MOSQUITTO_PORT="${MOSQUITTO_PORT:-1883}" \
      docker run -d \
        --name mosquitto \
        -p "$MOSQUITTO_PORT:1883" \
        -v "$SCRIPT_DIR/../../.local/mosquitto/config/mosquitto.conf:/mosquitto/config/mosquitto.conf" \
        -v "$SCRIPT_DIR/../../.local/mosquitto/data:/mosquitto/data" \
        -v "$SCRIPT_DIR/../../.local/mosquitto/log:/mosquitto/log" \
        "$MOSQUITTO_IMAGE"
      echo "Mosquitto 启动完成: tcp://localhost:$MOSQUITTO_PORT"
      ;;

    *)
      echo "无效选择: $mqtt_choice"
      exit 1
      ;;
  esac
fi

echo ""
echo "=== Docker 安装完成 ==="
echo ""
echo "运行状态:"
docker ps --filter "name=influxdb" --filter "name=nanomq" --filter "name=mosquitto" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "停止所有: docker stop influxdb nanomq mosquitto 2>/dev/null; docker rm influxdb nanomq mosquitto 2>/dev/null"
echo ""
echo "下一步:"
echo "  1. 初始化 InfluxDB: bash scripts/init_influxdb_v2.sh"
echo "  2. 启动桥接服务: bash scripts/start_bridge.sh"
echo "  3. 运行冒烟测试: bash scripts/run_smoke_test.sh"