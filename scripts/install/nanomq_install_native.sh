#!/usr/bin/env bash
# nanoMQ 本机安装脚本（macOS / Windows Git Bash）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$SCRIPT_DIR/../../.local}"
NANOMQ_VERSION="0.24.13"

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

echo "=== nanoMQ 本机安装 ==="
echo "安装目录: $INSTALL_DIR"

PLATFORM="$(uname -s)"
mkdir -p "$INSTALL_DIR/nanomq"

case "$PLATFORM" in
  Darwin*)
    echo "检测到: macOS"
    ARCH="$(uname -m)"
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "Apple Silicon" ]; then
      FILE="nanomq-${NANOMQ_VERSION}-macos-arm64.tar.gz"
    else
      FILE="nanomq-${NANOMQ_VERSION}-macos-x86_64.tar.gz"
    fi
    URL="https://github.com/nanomq/nanomq/releases/download/${NANOMQ_VERSION}/${FILE}"
    echo "下载: $URL"
    curl -L -o "$INSTALL_DIR/nanomq/${FILE}" "$URL"
    tar -xzf "$INSTALL_DIR/nanomq/${FILE}" -C "$INSTALL_DIR/nanomq"
    echo "安装完成: $INSTALL_DIR/nanomq/bin/nanomq"
    ;;

  Linux*)
    echo "检测到: Linux，请使用 Docker 版或从源码编译"
    exit 1
    ;;

  MINGW*|MSYS*|CYGWIN*)
    echo "检测到: Windows (Git Bash)"
    FILE="nanomq-${NANOMQ_VERSION}-windows-x86_64.zip"
    URL="https://github.com/nanomq/nanomq/releases/download/${NANOMQ_VERSION}/${FILE}"
    echo "下载: $URL"
    curl -L -o "$INSTALL_DIR/nanomq/${FILE}" "$URL"
    unzip -o "$INSTALL_DIR/nanomq/${FILE}" -d "$INSTALL_DIR/nanomq"
    echo "安装完成: $INSTALL_DIR/nanomq/bin/nanomq.exe"
    ;;

  *)
    echo "不支持的平台: $PLATFORM"
    exit 1
    ;;
esac

echo ""
echo "启动: $INSTALL_DIR/nanomq/bin/nanomq start --conf $INSTALL_DIR/nanomq/config/nanomq.conf"