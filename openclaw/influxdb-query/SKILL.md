---
name: influxdb-query
description: 直接查询 InfluxDB v2 数据。当用户需要复杂 SQL 查询、多维度数据分析、或桥接服务 API 不足以满足需求时使用。
---

# influxdb-query

直接对接 InfluxDB v2 HTTP API 执行 Flux 查询，是桥接服务 `iot-mqtt-bridge` 的兜底技能。

## 适用任务

- 复杂时序数据查询（多条件过滤、聚合、统计）
- 跨设备数据分析
- 自定义时间范围和聚合维度
- 当 `iot-mqtt-bridge` API 不足以满足需求时的兜底方案

## 前置条件

1. InfluxDB v2 服务可访问（默认 `http://localhost:8086`）
2. 有效的 token（可从 `config.yaml` 或环境变量 `INFLUXDB_TOKEN` 获取）
3. Bucket 名称已知（默认 `iot_data`）

## 数据模型

参见 `references/data-model.md`

## 标准调用

1. 先确认 InfluxDB 可达：`health`
2. 根据查询需求选择工具：
   - `flux_query` - 执行 Flux 查询
   - `list_buckets` - 列出可用 bucket
3. 检查返回的 `success` 字段

## 故障排查

遇到问题时先查看 `references/troubleshooting.md`，包含：
- Health 检查失败的处理
- Token 认证失败的诊断
- Bucket 不存在的解决方案
- 查询无数据时的排查步骤
- 查询超时或性能问题的优化

## 资源

- 查询工具：`references/tools.md`
- Flux 示例：`references/flux-examples.md`
- 数据模型：`references/data-model.md`
- 故障排查：`references/troubleshooting.md`