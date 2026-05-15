# iot-mqtt-bridge 技能包（可直接复制）

本目录已按 OpenClaw 技能包方式整理，可直接整体复制到 OpenClaw 的 `skills/` 目录中使用。

## 建议目录名

`iot-mqtt-bridge`

## 目录内容

- `SKILL.md`：技能入口与触发说明
- `TOOLS.md`：工具定义与参数说明
- `AGENTS.md`：Agent 使用策略
- `scripts/adapter.sh`：实际调用 bridge API 的适配器

## 复制后最小检查

1. `scripts/adapter.sh` 可执行
2. 目标环境可访问 bridge 服务（默认 `http://localhost:8080`）
3. 设置环境变量（可选）：

```bash
export OPENCLAW_ADAPTER_BASE_URL=http://localhost:8080
```

## 快速自检

在技能目录下执行：

```bash
bash scripts/adapter.sh health
bash scripts/adapter.sh query_devices
```

若返回 JSON，说明技能包可被 OpenClaw 正常使用。
