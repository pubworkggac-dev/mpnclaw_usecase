#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SCRIPTS_DIR="$SCRIPT_DIR"

echo "=== MQTT-InfluxDB 本机完整安装 ==="

PLATFORM="$(uname -s)"
echo "检测平台: $PLATFORM"

DEFAULT_INSTALL_DIR="$SCRIPT_DIR/../../.local"
INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

echo ""
echo "请指定安装目录 (默认: $DEFAULT_INSTALL_DIR):"
read -r user_install_dir
if [ -n "$user_install_dir" ]; then
  INSTALL_DIR="$user_install_dir"
fi
echo "安装目录: $INSTALL_DIR"

mkdir -p "$INSTALL_DIR/influxdb2"
mkdir -p "$INSTALL_DIR/nanomq"

echo ""
echo "请选择要安装的组件（逗号分隔，如 1,2 或 all）:"
echo "  1. InfluxDB"
echo "  2. MQTT Broker (nanoMQ / Mosquitto)"
echo "  3. 全部组件"
echo ""
echo "默认: 3 (全部)"
read -r choice
choice="${choice:-3}"

select_all=false
if [ "$choice" = "3" ] || [ "$choice" = "all" ]; then
  select_all=true
fi

install_influxdb=false
install_broker=false

if $select_all; then
  install_influxdb=true
  install_broker=true
else
  IFS=',' read -ra COMPONENTS <<< "$choice"
  for comp in "${COMPONENTS[@]}"; do
    comp="$(echo "$comp" | tr -d ' ')"
    case "$comp" in
      1) install_influxdb=true ;;
      2) install_broker=true ;;
    esac
  done
fi

if $install_influxdb; then
  echo ""
  echo "[1/2] 安装 InfluxDB..."

  case "$PLATFORM" in
    Darwin*)
      if ! command -v brew >/dev/null 2>&1; then
        echo "未找到 Homebrew，请先安装: https://brew.sh"
        exit 1
      fi
      brew install influxdb
      echo "InfluxDB 安装完成"
      echo "启动: brew services start influxdb"
      ;;

    Linux*)
      if command -v apt-get >/dev/null 2>&1; then
        echo "请通过官方 InfluxData 源安装: https://docs.influxdata.com/influxdb/v2/install/?platform=linux"
      else
        echo "请手动下载: https://portal.influxdata.com/downloads/"
      fi
      ;;

    MINGW*|MSYS*|CYGWIN*)
      if ! command -v winget >/dev/null 2>&1; then
        echo "未找到 winget，请从 https://portal.influxdata.com/downloads/ 手动下载"
        exit 1
      fi
      winget install --id InfluxData.InfluxDB.OSS -e --accept-source-agreements --accept-package-agreements
      echo "InfluxDB 安装完成"
      ;;

    *)
      echo "不支持的平台: $PLATFORM"
      exit 1
      ;;
  esac
fi

if $install_broker; then
  echo ""
  echo "[2/2] 安装 MQTT Broker..."

  echo "请选择 Broker (1 = nanoMQ, 2 = Mosquitto，默认: 1):"
  read -r broker_choice
  broker_choice="${broker_choice:-1}"

  case "$broker_choice" in
    1|nanomq)
      echo "安装 nanoMQ..."

      case "$PLATFORM" in
        Darwin*)
          ARCH="$(uname -m)"
          if [ "$ARCH" = "arm64" ]; then
            FILE="nanomq-0.24.13-macos-arm64.tar.gz"
          else
            FILE="nanomq-0.24.13-macos-x86_64.tar.gz"
          fi
          URL="https://github.com/nanomq/nanomq/releases/download/0.24.13/${FILE}"
          curl -L -o "$INSTALL_DIR/nanomq/${FILE}" "$URL"
          tar -xzf "$INSTALL_DIR/nanomq/${FILE}" -C "$INSTALL_DIR/nanomq"
          echo "nanoMQ 安装完成: $INSTALL_DIR/nanomq/bin/nanomq"
          ;;

        Linux*)
          echo "Linux 请使用 Docker 版 nanoMQ 或从源码编译"
          ;;

        MINGW*|MSYS*|CYGWIN*)
          FILE="nanomq-0.24.13-windows-x86_64.zip"
          URL="https://github.com/nanomq/nanomq/releases/download/0.24.13/${FILE}"
          curl -L -o "$INSTALL_DIR/nanomq/${FILE}" "$URL"
          unzip -o "$INSTALL_DIR/nanomq/${FILE}" -d "$INSTALL_DIR/nanomq"
          echo "nanoMQ 安装完成: $INSTALL_DIR/nanomq/bin/nanomq.exe"
          ;;

        *)
          echo "不支持的平台"
          exit 1
          ;;
      esac
      ;;

    2|mosquitto)
      echo "安装 Mosquitto..."

      case "$PLATFORM" in
        Darwin*)
          if ! command -v brew >/dev/null 2>&1; then
            echo "未找到 Homebrew"
            exit 1
          fi
          brew install mosquitto
          echo "Mosquitto 安装完成"
          ;;

        Linux*)
          if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get install -y mosquitto mosquitto-clients
          else
            echo "请使用系统包管理器安装"
          fi
          ;;

        MINGW*|MSYS*|CYGWIN*)
          if ! command -v winget >/dev/null 2>&1; then
            echo "请从 https://mosquitto.org/download/ 下载"
            exit 1
          fi
          winget install --id EclipseFoundation.Mosquitto -e --accept-source-agreements --accept-package-agreements
          echo "Mosquitto 安装完成"
          ;;

        *)
          echo "不支持的平台"
          exit 1
          ;;
      esac
      ;;

    *)
      echo "无效选择: $broker_choice"
      exit 1
      ;;
  esac
fi

echo ""
echo "=== 本机安装完成 ==="
echo ""
echo "安装目录: $INSTALL_DIR"
echo ""
echo "启动方式:"
if $install_influxdb; then
  case "$PLATFORM" in
    Darwin*)
      echo "  InfluxDB: brew services start influxdb"
      ;;
    MINGW*|MSYS*|CYGWIN*)
      echo "  InfluxDB: influxd (或通过开始菜单)"
      ;;
  esac
fi
if $install_broker; then
  case "$broker_choice" in
    1|nanomq)
      echo "  nanoMQ: $INSTALL_DIR/nanomq/bin/nanomq start --conf $INSTALL_DIR/nanomq/config/nanomq.conf"
      ;;
    2|mosquitto)
      echo "  Mosquitto: mosquitto -c /opt/homebrew/etc/mosquitto/mosquitto.conf (macOS)"
      ;;
  esac
fi
echo ""
echo "下一步:"
echo "  1. 启动各组件"
echo "  2. 初始化 InfluxDB: bash scripts/init_influxdb_v2.sh"
echo "  3. 启动桥接: bash scripts/start_bridge.sh"
echo "  4. 运行冒烟测试: bash scripts/run_smoke_test.sh"