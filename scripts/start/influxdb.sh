#!/usr/bin/env bash
# 启动 InfluxDB（本地）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env_common.sh
source "$SCRIPT_DIR/../env_common.sh"

DATA_ROOT_V2="${INSTALL_DIR:-"$MQTT_INFLUX_CASE_ROOT/.local"}/influxdb2"

mkdir -p "$DATA_ROOT_V2/engine"

bin_base() {
  local b
  b=$(basename "$1")
  b="${b%.exe}"
  printf '%s' "$b"
}

find_v2_in_path() {
  local n
  for n in influxd influxd.exe; do
    if command -v "$n" >/dev/null 2>&1; then
      command -v "$n"
      return 0
    fi
  done
  return 1
}

find_v2_default_windows_path() {
  local win_path
  local localappdata
  localappdata="${LOCALAPPDATA:-}"
  for win_path in \
    "/c/Users/Administrator/AppData/Local/Microsoft/WinGet/Packages/InfluxData.InfluxDB.OSS_Microsoft.Winget.Source_8wekyb3d8bbwe/influxd.exe" \
    "$localappdata/Microsoft/WinGet/Packages/InfluxData.InfluxDB.OSS_Microsoft.Winget.Source_8wekyb3d8bbwe/influxd.exe"
  do
    if [ -f "$win_path" ]; then
      printf '%s' "$win_path"
      return 0
    fi
  done
  return 1
}

BIN_V2=""

if [ -n "${INFLUXDB_NATIVE_BIN:-}" ]; then
  if [ ! -f "$INFLUXDB_NATIVE_BIN" ]; then
    echo "INFLUXDB_NATIVE_BIN 不是可执行文件路径: $INFLUXDB_NATIVE_BIN"
    exit 1
  fi
  base="$(bin_base "$INFLUXDB_NATIVE_BIN")"
  case "$base" in
    influxd) BIN_V2="$INFLUXDB_NATIVE_BIN" ;;
    *)
      echo "无法从文件名识别版本: $base（应为 influxd），请改用 PATH 安装或重命名。"
      exit 1
      ;;
  esac
else
  BIN_V2=""
  if v2path="$(find_v2_in_path 2>/dev/null)"; then
    BIN_V2="$v2path"
  elif v2path="$(find_v2_default_windows_path 2>/dev/null)"; then
    BIN_V2="$v2path"
  fi
fi

if [ -z "${BIN_V2:-}" ]; then
  echo "未找到 influxd。请将安装目录加入 PATH，或设置 INFLUXDB_NATIVE_BIN。"
  exit 1
fi

echo "InfluxDB OSS v2（本机）: $BIN_V2"
echo "请将 influxdb.url 设为 http://localhost:8086，或在启动桥接前 export INFLUXDB_URL=http://localhost:8086。"
echo "bolt: $DATA_ROOT_V2/influxd.bolt  engine: $DATA_ROOT_V2/engine"
echo
RUNTIME_CONFIG="$DATA_ROOT_V2/influxd.runtime.toml"
: > "$RUNTIME_CONFIG"
# shellcheck disable=SC2086
export INFLUXD_CONFIG_PATH="$RUNTIME_CONFIG"
exec "$BIN_V2" \
  --bolt-path="$DATA_ROOT_V2/influxd.bolt" \
  --engine-path="$DATA_ROOT_V2/engine" \
  ${INFLUXD_EXTRA_ARGS:-}