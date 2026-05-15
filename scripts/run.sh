#!/usr/bin/env bash
# MQTT-InfluxDB 一键启动脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env_common.sh"

show_help() {
  cat <<EOF
用法: bash scripts/run.sh <命令>

命令:
  install              一键安装（Docker 或本机）
  init                初始化 InfluxDB
  start [模式]        启动服务
  stop                停止所有服务
  test                运行冒烟测试
  help                显示帮助

启动模式 (start 命令):
  native              本机模式（各组件前台启动）
  docker [方案]       Docker 模式（二选一）
  all                 本机 + Docker Compose 一起启动

Docker 方案:
  nanomq              InfluxDB + nanoMQ
  mosquitto           InfluxDB + Mosquitto

示例:
  bash scripts/run.sh install                     # 一键安装
  bash scripts/run.sh init                        # 初始化 InfluxDB
  bash scripts/run.sh start                       # 显示启动指南
  bash scripts/run.sh start native               # 本机模式启动
  bash scripts/run.sh start docker nanomq        # Docker 启动 (nanoMQ)
  bash scripts/run.sh start docker mosquitto     # Docker 启动 (Mosquitto)
  bash scripts/run.sh stop                        # 停止所有服务
  bash scripts/run.sh test                        # 运行冒烟测试

单组件操作:
  bash scripts/init/influxdb_v2.sh              # 初始化 InfluxDB
  bash scripts/start/influxdb.sh               # 启动 InfluxDB（本机）
  bash scripts/start/influxdb_docker.sh         # 启动 InfluxDB（Docker）
  bash scripts/start/nanomq.sh                  # 启动 nanoMQ
  bash scripts/start/mosquitto.sh               # 启动 Mosquitto
  bash scripts/start/bridge.sh                 # 启动桥接服务
  bash scripts/test/smoke.sh                    # 运行冒烟测试
EOF
}

start_docker() {
  local compose_file=""
  case "${1:-nanomq}" in
    nanomq)
      compose_file="$SCRIPT_DIR/install/docker-compose.nanomq.yml"
      ;;
    mosquitto)
      compose_file="$SCRIPT_DIR/install/docker-compose.mosquitto.yml"
      ;;
    *)
      echo "未知 Docker 方案: $1"
      echo "方案: nanomq, mosquitto"
      exit 1
      ;;
  esac

  if ! command -v docker >/dev/null 2>&1; then
    echo "错误: 未找到 docker 命令"
    exit 1
  fi

  local compose_cmd="docker compose"
  if ! docker compose version >/dev/null 2>&1; then
    compose_cmd="docker-compose"
    if ! command -v docker-compose >/dev/null 2>&1; then
      echo "错误: 未找到 docker compose"
      exit 1
    fi
  fi

  echo "启动 Docker 服务: $1"
  echo "配置: $compose_file"
  echo ""
  cd "$SCRIPT_DIR/install"
  $compose_cmd -f "$compose_file" up
}

start_native() {
  echo "请在各自的终端中运行以下命令："
  echo ""
  echo "终端 1 - InfluxDB:"
  echo "  bash scripts/start/influxdb.sh"
  echo "  或 bash scripts/start/influxdb_docker.sh"
  echo ""
  echo "终端 2 - MQTT Broker (二选一):"
  echo "  bash scripts/start/nanomq.sh"
  echo "  bash scripts/start/mosquitto.sh"
  echo ""
  echo "终端 3 - 桥接服务:"
  echo "  bash scripts/start/bridge.sh"
  echo ""
  echo "终端 4 - 冒烟测试:"
  echo "  bash scripts/test/smoke.sh"
}

case "${1:-help}" in
  install)
    exec bash "$SCRIPT_DIR/install/install.sh"
    ;;
  init)
    exec bash "$SCRIPT_DIR/init/influxdb_v2.sh"
    ;;
  start)
    shift
    case "${1:-}" in
      native)
        start_native
        ;;
      docker)
        shift
        start_docker "${1:-nanomq}"
        ;;
      all)
        echo "=== 本机模式 ==="
        start_native
        ;;
      nanomq|mosquitto)
        start_docker "$1"
        ;;
      -h|--help|help)
        show_help
        ;;
      "")
        echo "请指定启动模式: native, docker [nanomq|mosquitto]"
        echo ""
        echo "示例:"
        echo "  bash scripts/run.sh start native               # 本机模式"
        echo "  bash scripts/run.sh start docker nanomq        # Docker nanoMQ"
        echo "  bash scripts/run.sh start docker mosquitto      # Docker Mosquitto"
        echo ""
        show_help
        exit 1
        ;;
      *)
        echo "未知模式: $1"
        echo ""
        show_help
        exit 1
        ;;
    esac
    ;;
  stop)
    echo "停止 Docker 容器..."
    docker stop mqtt-influxdb-influx2 nanomq mosquitto 2>/dev/null || true
    docker rm mqtt-influxdb-influx2 nanomq mosquitto 2>/dev/null || true
    echo "停止完成"
    ;;
  test)
    exec bash "$SCRIPT_DIR/test/smoke.sh" "$@"
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    echo "未知命令: $1"
    echo ""
    show_help
    exit 1
    ;;
esac