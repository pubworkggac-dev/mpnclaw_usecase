# Test Design: MQTT-InfluxDB Bridge 九井云协议测试

> 设计者：Sisyphus
> 日期：2026-05-14
> 目标：为 `usecase/1.mqtt_influxdb` 补充缺失的单元测试，覆盖 command reply、OTA、profile download 等九井云协议场景

---

## 第零步：最小澄清

- **测试对象**：九井云协议解析与处理链路（`src/mqtt/handler.py`、`src/adapters/jiujingyun.py`）
- **核心业务规则**：
  1. Command reply 必须通过 `payload.id` 与下发的 `message_id` 匹配
  2. OTA/upgrade/process 的 `step` 字段必须单调递增，最终为 100
  3. 所有 reply 的 `code` 字段必须为 200 才算成功
- **失败语义**：`data.Code != "0"` 表示设备执行失败；`code != 200` 表示协议错误
- **本次交付**：pytest 测试文件（`tests/test_jiujing_protocol.py`），含 docstring + TC ID

---

## 第一步：业务约束建模

| 约束ID | 业务规则 | 违反后的业务影响 |
|--------|----------|-----------------|
| B1 | Command reply 的 `id` 字段必须与下发的 `message_id` 一致 | Bridge 无法匹配回复，导致命令永远 pending |
| B2 | Command reply 的 `code` 必须为 200 才表示协议层成功 | Agent 误判命令已成功，实际设备未收到 |
| B3 | Command reply 的 `data.Code` 为 "0" 才表示设备执行成功 | Agent 误判设备执行成功，实际失败被忽略 |
| B4 | OTA upgrade/process 的 `detail_id` 必须在各轮交互中保持一致 | OTA 流程无法关联，导致升级状态分裂 |
| B5 | OTA upgrade/process 的 `step` 必须单调递增（0→100），不能倒退 | 升级状态机异常，可能出现不可逆状态 |
| B6 | Profile download/process 的 `download_url` 非空且 `fail` 为空才表示成功 | 配置文件获取结果被误判为成功 |
| B7 | 所有九井云格式消息的 `method` 字段必须被正确识别 | 消息被错误归类或静默丢弃 |

---

## 第二步：系统不变量定义

1. **Reply ID 一致性**：下发的 `message_id` 与设备回复的 `id` 必须完全相等（字符串比对）
2. **Reply Topic 与 Service 对应**：`_reply` topic 的 service name 必须与下发 topic 一致
3. **Code 200 契约**：`code != 200` 的回复在协议层面已失败，不应标记为命令执行成功
4. **Data.Code 执行语义**：`data.Code == "0"` 是设备执行成功的金标准
5. **OTA Step 单调性**：同一 `detail_id` 的 `step` 值只增不减，直到 100
6. **Protocol Method 解析路径**：
   - `thing.property.post` → 遥测存储
   - `thing.service.*` → 命令处理
   - `ota/upgrade` → OTA 下发（不通 bridged）
   - `ota/upgrade/process` → OTA 进度（不通 bridged）
   - `profile/download/process` → 配置文件获取结果（不通 bridged）

---

## 第三步：错误模型分析

| 错误模型 | 说明 | 关联约束 |
|----------|------|----------|
| Off-by-one | step 从 50 跳到 100（跳过中间值）但能完成 | B5 |
| 边界折叠 | code=200 但 data.Code="-1"（设备执行失败被忽略） | B2, B3 |
| ID 不匹配 | reply.id 与下发 message_id 不一致（空格/大小写问题） | B1 |
| 静默丢弃 | ota/upgrade/process 消息因 method 不识别被丢弃 | B7 |
| 状态未重置 | 同一 device 的并发命令 reply 相互覆盖 | B1 |
| 超时未处理 | reply 超时后无状态更新，Agent 一直等待 | B1 |

---

## 第四步：测试分类设计（场景组合表）

| 测试类型 | 关键变量组合 | 目标错误模型 | 保护语义 | 优先级 |
|----------|--------------|--------------|----------|--------|
| 正常场景-R1 | `code=200, data.Code="0", id 匹配` | 无 | Reply 被正确处理并关联到下发命令 | P0 |
| 正常场景-R2 | `code=200, data.Code="0", step=100, fail=null` | 无 | OTA 升级最终成功状态被正确解析 | P0 |
| 正常场景-R3 | `code=200, download_url 非空, fail=null` | 无 | Profile download 成功结果被正确解析 | P0 |
| 边界场景-R4 | `code=200, data.Code="-1", id 不匹配` | ID 不匹配 + 执行失败 | Agent 能区分协议成功与执行失败 | P1 |
| 边界场景-R5 | `code=200, step=50→100（跳过中间）` | Off-by-one | step 跳跃被接受（协议允许跳跃） | P2 |
| 异常场景-R6 | `code=400, data.Code="0"` | 边界折叠 | code 非 200 时被识别为协议层失败 | P1 |
| 异常场景-R7 | `code=200, data.Code="0", id=null` | ID 不匹配 | id 为 null 时不 crash，静默记录 | P1 |
| 组合场景-R8 | 并发两个 command reply（不同 message_id） | 状态未重置 | 每个 reply 被正确关联到各自的下发 | P0 |

---

## 第五步：TC ID 列表及约束映射

| TC ID | 测试场景 | 约束ID | 不变量 |
|-------|----------|--------|--------|
| TC-REPLY-001 | Command reply 解析——code=200, data.Code="0", id 匹配 | B1, B2, B3 | Reply 被正确处理并关联到下发命令 |
| TC-REPLY-002 | Command reply 解析——code=200, data.Code="-1"（设备执行失败） | B2, B3 | Agent 能区分协议成功与执行失败 |
| TC-REPLY-003 | Command reply 解析——code 非 200（协议错误） | B2 | code 非 200 被识别为协议层失败 |
| TC-REPLY-004 | Command reply 解析——id 为 null | B1 | id 为 null 时不 crash，静默记录 |
| TC-REPLY-005 | Command reply 解析——id 不匹配（空格问题） | B1 | ID 不匹配时能被检测 |
| TC-REPLY-006 | 并发两个 command reply（不同 message_id） | B1 | 每个 reply 被正确关联到各自的下发 |
| TC-OTA-001 | OTA upgrade/process 解析——step=100, fail=null（成功） | B4, B5, B7 | OTA 成功状态被正确解析 |
| TC-OTA-002 | OTA upgrade/process 解析——step=50, fail 非空（失败） | B4, B5, B7 | OTA 失败状态被正确解析 |
| TC-OTA-003 | OTA upgrade/process 解析——step 跳跃（50→100） | B5, B7 | step 跳跃被接受 |
| TC-OTA-004 | OTA upgrade/process 解析——detail_id 与下发不一致 | B4 | detail_id 不一致时被检测 |
| TC-PROFILE-001 | Profile download/process 解析——download_url 非空, fail=null | B6, B7 | 下载成功状态被正确解析 |
| TC-PROFILE-002 | Profile download/process 解析——fail 非空（失败） | B6, B7 | 下载失败状态被正确解析 |
| TC-PROFILE-003 | Profile download/process 解析——download_url 为空 | B6 | download_url 为空时能正确处理 |

---

## 第六步：全局测试目录（新建）

| TC ID | 自动化位置 | 状态 | 约束ID |
|-------|----------|------|--------|
| TC-REPLY-001 | `tests/test_jiujing_protocol.py::test_command_reply_parse_success` | TODO | B1, B2, B3 |
| TC-REPLY-002 | `tests/test_jiujing_protocol.py::test_command_reply_parse_device_failure` | TODO | B2, B3 |
| TC-REPLY-003 | `tests/test_jiujing_protocol.py::test_command_reply_parse_protocol_error` | TODO | B2 |
| TC-REPLY-004 | `tests/test_jiujing_protocol.py::test_command_reply_parse_null_id` | TODO | B1 |
| TC-REPLY-005 | `tests/test_jiujing_protocol.py::test_command_reply_parse_id_mismatch` | TODO | B1 |
| TC-REPLY-006 | `tests/test_jiujing_protocol.py::test_command_reply_parse_concurrent` | TODO | B1 |
| TC-OTA-001 | `tests/test_jiujing_protocol.py::test_ota_upgrade_process_parse_success` | TODO | B4, B5, B7 |
| TC-OTA-002 | `tests/test_jiujing_protocol.py::test_ota_upgrade_process_parse_failure` | TODO | B4, B5, B7 |
| TC-OTA-003 | `tests/test_jiujing_protocol.py::test_ota_upgrade_process_parse_step_skip` | TODO | B5, B7 |
| TC-OTA-004 | `tests/test_jiujing_protocol.py::test_ota_upgrade_process_parse_detail_id_mismatch` | TODO | B4 |
| TC-PROFILE-001 | `tests/test_jiujing_protocol.py::test_profile_download_process_parse_success` | TODO | B6, B7 |
| TC-PROFILE-002 | `tests/test_jiujing_protocol.py::test_profile_download_process_parse_failure` | TODO | B6, B7 |
| TC-PROFILE-003 | `tests/test_jiujing_protocol.py::test_profile_download_process_parse_empty_url` | TODO | B6 |

---

## 第七步：测试设计说明

### 数据流分析

**Command Reply 解析链路**：
```
MQTT _reply Topic(/system/pk/dk/thing/service/SetDeviceName_reply)
  → MqttClient._on_message
    → _reply_queue.put()                    ← 按 topic 后缀 "_reply" 判别
      → _reply_consumer() 消费队列
        → handle_command_reply()            ← 解析 payload.id
          → asyncio.create_task(on_command_reply())
            → 更新 _commands_map + 取消超时 + WS sessions.send 推送
```

**关键函数**：
- `handle_command_reply(payload: dict)` — 解析 MQTT reply JSON，提取 `payload.id` 作为 message_id，调度 `on_command_reply`

**OTA/Profile 解析链路**：
```
MQTT Topic(/system/pk/dk/ota/upgrade/process)
  → MqttClient._on_message
    → handler(None, None, FakeMessage(topic, payload))
      → FormatRouter.parse(topic, payload)
        → JiujingyunAdapter.parse(topic, payload)
          → 检测 method == "ota.upgrade.process" 或 "profile.download.process"
            → 返回 None（不通 bridged）
```

### 测试策略

1. **单元测试**：直接测试 `handle_command_reply()` 解析逻辑，使用 mock MQTT message
2. **契约测试**：验证九井云 reply 格式（code/data.Code/id）与代码解析的契约匹配
3. **边界测试**：验证非法 id 格式、空值、错误 code 的处理

---

## 第八步：这些测试能够拦截的错误实现类型

| 错误实现 | 检测测试 |
|----------|----------|
| reply 解析时 `id` 取错字段（如取 `message_id` 而非 `id`） | TC-REPLY-001, TC-REPLY-005 |
| `code != 200` 时仍进入成功分支 | TC-REPLY-003 |
| `data.Code != "0"` 时仍标记为成功 | TC-REPLY-002 |
| OTA step 递减时未校验 | TC-OTA-003 |
| detail_id 不一致时未校验 | TC-OTA-004 |
| download_url 为空时未校验 | TC-PROFILE-003 |
| 并发 reply 时状态被覆盖 | TC-REPLY-006 |

---

## 参考文档

- `docs/reference/4.jiujing_设备功能.md` — Command 下发与回复格式
- `docs/reference/5.jiujing_ota升级.md` — OTA upgrade/process 格式
- `docs/reference/6.jiujing_获取设备配置文件或日志文件.md` — profile/download/process 格式
- `src/mqtt/handler.py` — Message handler 实现
- `src/adapters/jiujingyun.py` — JiujingyunAdapter 实现
- `src/api/routes.py:231-251` — `handle_command_reply()` 实现