#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$SCRIPT_DIR/../../.local}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --help)
      echo "用法: $0 [--install-dir /path/to/tools]"
      exit 0
      ;;
    *)
      shift
      ;;
  esac
done

echo "=== Mosquitto 本机安装 ==="
echo "安装目录: $INSTALL_DIR"

PLATFORM="$(uname -s)"
case "$PLATFORM" in
  Darwin*)
    echo "检测到: macOS"

    if ! command -v brew >/dev/null 2>&1; then
      echo "未找到 Homebrew，请先安装: https://brew.sh"
      exit 1
    fi

    echo "安装 Mosquitto..."
    brew install mosquitto
    echo "安装完成"
    ;;

  Linux*)
    echo "检测到: Linux"
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get install -y mosquitto mosquitto-clients
    else
      echo "请使用系统包管理器安装 mosquitto"
    fi
    ;;

  MINGW*|MSYS*|CYGWIN*)
    echo "检测到: Windows (Git Bash)"

    if ! command -v winget >/dev/null 2>&1; then
      echo "未找到 winget，请从 https://mosquitto.org/download/ 下载手动安装。"
      exit 1
    fi

    echo "安装 Mosquitto..."
    winget install --id EclipseFoundation.Mosquitto -e --accept-source-agreements --accept-package-agreements
    echo "安装完成: /c/Program Files/mosquitto/mosquitto.exe"
    ;;

  *)
    echo "不支持的平台: $PLATFORM"
    exit 1
    ;;
esac

echo ""
echo "启动: mosquitto -c /path/to/config.conf"