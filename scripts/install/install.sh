#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== MQTT-InfluxDB 一键安装 ==="
echo ""

PLATFORM="$(uname -s)"
echo "检测平台: $PLATFORM"

echo ""
echo "请选择安装方式:"
echo "  1. Docker 安装 (推荐，需要 Docker Desktop)"
echo "  2. 本机安装 (直接安装到系统)"
echo ""
echo "默认: 1"
read -r install_mode
install_mode="${install_mode:-1}"

case "$install_mode" in
  1|docker)
    echo ""
    echo "检查 Docker..."

    if ! command -v docker >/dev/null 2>&1; then
      echo "错误: 未找到 docker 命令"
      echo ""
      echo "请先安装 Docker Desktop:"
      echo "  macOS: https://docs.docker.com/desktop/install/mac-install/"
      echo "  Windows: https://docs.docker.com/desktop/install/windows-install/"
      echo "  Linux: https://docs.docker.com/desktop/install/linux-install/"
      echo ""
      echo "或选择 2 进行本机安装"
      exit 1
    fi

    echo "Docker 版本:"
    docker --version

    if ! docker info >/dev/null 2>&1; then
      echo "错误: Docker 未运行，请启动 Docker Desktop"
      exit 1
    fi

    echo ""
    echo "使用 Docker 安装..."
    exec bash "$SCRIPT_DIR/install_docker.sh"
    ;;

  2|native|local|本地)
    echo ""
    echo "使用本机安装..."
    exec bash "$SCRIPT_DIR/install_native.sh"
    ;;

  *)
    echo "无效选择: $install_mode"
    exit 1
    ;;
esac