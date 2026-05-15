#!/usr/bin/env bash
# InfluxDB 本机安装脚本（macOS / Windows Git Bash / Linux）
#
# 用法:
#   bash install/influxdb_install_native.sh
#   bash install/influxdb_install_native.sh --install-dir /path/to/tools
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SCRIPTS_DIR="$SCRIPT_DIR"

# 默认安装目录
DEFAULT_INSTALL_DIR="$SCRIPT_DIR/../../.local"
INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

# 解析参数
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
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

echo "=== InfluxDB 本机安装 ==="
echo "安装目录: $INSTALL_DIR"

PLATFORM="$(uname -s)"
case "$PLATFORM" in
  Darwin*)
    echo "检测到: macOS"

    if ! command -v brew >/dev/null 2>&1; then
      echo "未找到 Homebrew，请先安装: https://brew.sh"
      exit 1
    fi

    echo "安装 InfluxDB..."
    brew install influxdb

    INFLUXDB_BIN="$(brew --prefix)/bin/influxd"
    echo "安装完成: $INFLUXDB_BIN"
    echo "启动服务: brew services start influxdb"
    ;;

  Linux*)
    echo "检测到: Linux"

    if command -v apt-get >/dev/null 2>&1; then
      echo "检测到 apt，推荐通过官方 InfluxData 源安装"
      echo "请参考: https://docs.influxdata.com/influxdb/v2/install/?platform=linux"
      echo "或手动下载: https://portal.influxdata.com/downloads/"
      exit 1
    fi
    ;;

  MINGW*|MSYS*|CYGWIN*)
    echo "检测到: Windows (Git Bash)"

    if ! command -v winget >/dev/null 2>&1; then
      echo "未找到 winget，请从 https://github.com/nanomq/nanomq/releases 下载手动安装。"
      exit 1
    fi

    echo "安装 InfluxDB OSS..."
    winget install --id InfluxData.InfluxDB.OSS -e --accept-source-agreements --accept-package-agreements

    # 查找安装路径
    localappdata="${LOCALAPPDATA:-}"
    INFLUXDB_BIN="$localappdata/Microsoft/WinGet/Packages/InfluxData.InfluxDB.OSS_Microsoft.Winget.Source_8wekyb3d8bbwe/influxd.exe"

    if [ ! -f "$INFLUXDB_BIN" ]; then
      echo "安装成功，请手动查找 influxd.exe 并加入 PATH"
    else
      echo "安装完成: $INFLUXDB_BIN"
    fi
    ;;

  *)
    echo "不支持的平台: $PLATFORM"
    exit 1
    ;;
esac

echo ""
echo "后续步骤:"
echo "  1. 启动 InfluxDB: influxd 或 brew services start influxdb"
echo "  2. 初始化: bash scripts/init_influxdb_v2.sh"
echo "  3. 或使用一键安装: bash scripts/install.sh"