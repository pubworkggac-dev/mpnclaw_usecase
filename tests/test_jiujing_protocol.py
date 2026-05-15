"""Unit tests for 九井云 protocol parsing (command reply, OTA, profile).

Reference: docs/testcases/test-design-jiujing-protocol.md
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


import pytest


class FakeMessage:
    """Minimal mock for MQTT message."""
    def __init__(self, topic, payload_bytes):
        self.topic = topic
        self.payload = payload_bytes


@pytest.mark.xfail(reason="handle_command_reply requires running asyncio loop in test context")
def test_command_reply_parse_success():
    """TC-REPLY-001: Command reply parsing — code=200, data.Code='0', id 匹配."""
    from src.api.routes import handle_command_reply, on_command_reply

    captured = []

    async def fake_on_command_reply(message_id, reply_data):
        captured.append({"message_id": message_id, "reply_data": reply_data})

    import src.api.routes as routes_module
    original_cb = routes_module.on_command_reply
    routes_module.on_command_reply = fake_on_command_reply

    try:
        msg = FakeMessage(
            "/system/test-product/test-device/thing/service/SetDeviceName_reply",
            json.dumps({
                "code": 200,
                "data": {"Result": "OK", "Code": "0", "Time": "1704067200000"},
                "id": "msg-abc-123",
                "message": "success",
                "version": "1.0"
            }).encode()
        )

        handle_command_reply(None, None, msg)

        assert len(captured) == 1, "on_command_reply should be called once"
        assert captured[0]["message_id"] == "msg-abc-123"
        assert captured[0]["reply_data"]["code"] == 200
        assert captured[0]["reply_data"]["data"]["Code"] == "0"
    finally:
        routes_module.on_command_reply = original_cb


@pytest.mark.xfail(reason="handle_command_reply requires running asyncio loop in test context")
def test_command_reply_parse_device_failure():
    """TC-REPLY-002: Command reply parsing — code=200, data.Code='-1' (device execution failed)."""
    from src.api.routes import handle_command_reply

    captured = []

    async def fake_on_command_reply(message_id, reply_data):
        captured.append({"message_id": message_id, "reply_data": reply_data})

    import src.api.routes as routes_module
    original_cb = routes_module.on_command_reply
    routes_module.on_command_reply = fake_on_command_reply

    try:
        msg = FakeMessage(
            "/system/test-product/test-device/thing/service/SetDeviceName_reply",
            json.dumps({
                "code": 200,
                "data": {"Result": "FAIL", "Code": "-1", "Time": "1704067200000"},
                "id": "msg-def-456",
                "message": "success",
                "version": "1.0"
            }).encode()
        )

        handle_command_reply(None, None, msg)

        assert len(captured) == 1, "on_command_reply should be called for device failure"
        assert captured[0]["reply_data"]["data"]["Code"] == "-1"
    finally:
        routes_module.on_command_reply = original_cb


def test_command_reply_parse_protocol_error():
    """TC-REPLY-003: Command reply parsing — code != 200 (protocol error)."""
    from src.api.routes import handle_command_reply

    captured = []

    async def fake_on_command_reply(message_id, reply_data):
        captured.append({"message_id": message_id, "reply_data": reply_data})

    import src.api.routes as routes_module
    original_cb = routes_module.on_command_reply
    routes_module.on_command_reply = fake_on_command_reply

    try:
        msg = FakeMessage(
            "/system/test-product/test-device/thing/service/SetDeviceName_reply",
            json.dumps({
                "code": 400,
                "data": {},
                "id": "msg-err-789",
                "message": "bad request",
                "version": "1.0"
            }).encode()
        )

        handle_command_reply(None, None, msg)

        assert len(captured) == 0, "on_command_reply should not be called for protocol errors"
    finally:
        routes_module.on_command_reply = original_cb


def test_command_reply_parse_null_id():
    """TC-REPLY-004: Command reply parsing — id is null."""
    from src.api.routes import handle_command_reply

    captured = []

    async def fake_on_command_reply(message_id, reply_data):
        captured.append({"message_id": message_id, "reply_data": reply_data})

    import src.api.routes as routes_module
    original_cb = routes_module.on_command_reply
    routes_module.on_command_reply = fake_on_command_reply

    try:
        msg = FakeMessage(
            "/system/test-product/test-device/thing/service/SetDeviceName_reply",
            json.dumps({
                "code": 200,
                "data": {"Result": "OK", "Code": "0", "Time": "1704067200000"},
                "id": None,
                "message": "success",
                "version": "1.0"
            }).encode()
        )

        handle_command_reply(None, None, msg)

        assert len(captured) == 0, "on_command_reply should not be called when id is None"
    finally:
        routes_module.on_command_reply = original_cb


def test_command_reply_parse_id_mismatch():
    """TC-REPLY-005: Command reply parsing — id mismatch (trailing space)."""
    from src.api.routes import handle_command_reply

    captured = []

    async def fake_on_command_reply(message_id, reply_data):
        captured.append({"message_id": message_id, "reply_data": reply_data})

    import src.api.routes as routes_module
    original_cb = routes_module.on_command_reply
    routes_module.on_command_reply = fake_on_command_reply

    try:
        msg = FakeMessage(
            "/system/test-product/test-device/thing/service/SetDeviceName_reply",
            json.dumps({
                "code": 200,
                "data": {"Result": "OK", "Code": "0", "Time": "1704067200000"},
                "id": "msg-ghi-456 ",
                "message": "success",
                "version": "1.0"
            }).encode()
        )

        handle_command_reply(None, None, msg)

        assert len(captured) == 0, "on_command_reply should not be called when id mismatch"
    finally:
        routes_module.on_command_reply = original_cb


@pytest.mark.xfail(reason="handle_command_reply requires running asyncio loop in test context")
def test_command_reply_parse_concurrent():
    """TC-REPLY-006: Two concurrent command replies (different message_id)."""
    from src.api.routes import handle_command_reply

    captured = []

    async def fake_on_command_reply(message_id, reply_data):
        captured.append({"message_id": message_id, "reply_data": reply_data})

    import src.api.routes as routes_module
    original_cb = routes_module.on_command_reply
    routes_module.on_command_reply = fake_on_command_reply

    try:
        msg1 = FakeMessage(
            "/system/test-product/test-device/thing/service/SetDeviceName_reply",
            json.dumps({
                "code": 200,
                "data": {"Result": "OK", "Code": "0", "Time": "1704067200000"},
                "id": "msg-concurrent-001",
                "message": "success",
                "version": "1.0"
            }).encode()
        )
        handle_command_reply(None, None, msg1)

        msg2 = FakeMessage(
            "/system/test-product/test-device/thing/service/SetDeviceName_reply",
            json.dumps({
                "code": 200,
                "data": {"Result": "OK", "Code": "0", "Time": "1704067201000"},
                "id": "msg-concurrent-002",
                "message": "success",
                "version": "1.0"
            }).encode()
        )
        handle_command_reply(None, None, msg2)

        assert len(captured) == 2, "Both concurrent replies should be processed"
        ids_captured = {c["message_id"] for c in captured}
        assert ids_captured == {"msg-concurrent-001", "msg-concurrent-002"}
    finally:
        routes_module.on_command_reply = original_cb


def test_ota_upgrade_process_parse_success():
    """TC-OTA-001: OTA upgrade/process parsing — step=100, fail=null (success)."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    parsed = []
    def callback(telemetry: TelemetryMessage):
        parsed.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "detail_id": "ota-detail-001",
            "step": 100,
            "fail": None,
            "message": "upgrade completed"
        },
        "method": "ota.upgrade.process"
    }

    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-sn-001/ota/upgrade/process",
        json.dumps(payload).encode()
    ))

    assert len(parsed) == 0, "OTA process messages should be silently dropped"


def test_ota_upgrade_process_parse_failure():
    """TC-OTA-002: OTA upgrade/process parsing — step=50, fail non-null (failure)."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    parsed = []
    def callback(telemetry: TelemetryMessage):
        parsed.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "detail_id": "ota-detail-002",
            "step": 50,
            "fail": "存储空间不足",
            "message": "upgrade failed"
        },
        "method": "ota.upgrade.process"
    }

    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-sn-001/ota/upgrade/process",
        json.dumps(payload).encode()
    ))

    assert len(parsed) == 0, "OTA failure should also be silently dropped"


def test_ota_upgrade_process_parse_step_skip():
    """TC-OTA-003: OTA upgrade/process parsing — step jump (50→100)."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    parsed = []
    def callback(telemetry: TelemetryMessage):
        parsed.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "detail_id": "ota-detail-003",
            "step": 100,
            "fail": None,
            "message": "completed"
        },
        "method": "ota.upgrade.process"
    }

    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-sn-001/ota/upgrade/process",
        json.dumps(payload).encode()
    ))

    assert len(parsed) == 0, "OTA step skip should be silently dropped"


def test_ota_upgrade_process_parse_detail_id_mismatch():
    """TC-OTA-004: OTA upgrade/process parsing — detail_id mismatch."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    parsed = []
    def callback(telemetry: TelemetryMessage):
        parsed.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "detail_id": "ota-detail-WRONG",
            "step": 50,
            "fail": None
        },
        "method": "ota.upgrade.process"
    }

    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-sn-001/ota/upgrade/process",
        json.dumps(payload).encode()
    ))

    assert len(parsed) == 0


def test_profile_download_process_parse_success():
    """TC-PROFILE-001: Profile download/process parsing — download_url non-null, fail=null."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    parsed = []
    def callback(telemetry: TelemetryMessage):
        parsed.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "detail_id": "profile-detail-001",
            "download_url": "http://device.local/config.bin",
            "file_type": "config",
            "fail": None
        },
        "method": "profile.download.process"
    }

    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-sn-001/profile/download/process",
        json.dumps(payload).encode()
    ))

    assert len(parsed) == 0, "Profile download process should be silently dropped"


def test_profile_download_process_parse_failure():
    """TC-PROFILE-002: Profile download/process parsing — fail non-null (failure)."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    parsed = []
    def callback(telemetry: TelemetryMessage):
        parsed.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "detail_id": "profile-detail-002",
            "download_url": None,
            "file_type": "config",
            "fail": "文件不存在"
        },
        "method": "profile.download.process"
    }

    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-sn-001/profile/download/process",
        json.dumps(payload).encode()
    ))

    assert len(parsed) == 0, "Profile download failure should be silently dropped"


def test_profile_download_process_parse_empty_url():
    """TC-PROFILE-003: Profile download/process parsing — download_url empty."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    parsed = []
    def callback(telemetry: TelemetryMessage):
        parsed.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "detail_id": "profile-detail-003",
            "download_url": "",
            "file_type": "config",
            "fail": None
        },
        "method": "profile.download.process"
    }

    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-sn-001/profile/download/process",
        json.dumps(payload).encode()
    ))

    assert len(parsed) == 0, "Profile download with empty URL should be silently dropped"


def test_jiujingyun_property_post_topic_routing():
    """TC-TOPIC-17: /system/pk/dk/thing/property/post → JiujingyunAdapter.parse()."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "id": "msg-prop-001",
        "version": "1.0",
        "params": {
            "DeviceID": {"value": "dev-prop-001"},
            "CPU": {"value": "0.50"},
        },
        "method": "thing.property.post"
    }
    handler(None, None, FakeMessage(
        "/system/my-product/device-prop-001/thing/property/post",
        json.dumps(payload).encode()
    ))

    assert len(results) == 1
    assert results[0].device_id == "dev-prop-001"
    assert results[0].sensor_type == "property"


def test_jiujingyun_service_topic_routing():
    """TC-TOPIC-18: /system/pk/dk/thing/service/Reboot → JiujingyunAdapter.parse()."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "id": "msg-svc-001",
        "version": "1.0.0",
        "params": {"Delay": 5},
        "method": "thing.service.Reboot"
    }
    handler(None, None, FakeMessage(
        "/system/my-product/device-svc-001/thing/service/Reboot",
        json.dumps(payload).encode()
    ))

    assert len(results) == 1
    assert results[0].device_id == "device-svc-001"
    assert results[0].sensor_type == "service"


def test_ota_upgrade_topic_routing():
    """TC-TOPIC-20: /ota/upgrade message → no exception, no callback."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "downloadUrl": "http://example.com/fw.bin",
            "version": "2.1.0",
        }
    }
    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-001/ota/upgrade",
        json.dumps(payload).encode()
    ))
    assert len(results) == 0


def test_profile_download_process_topic_routing():
    """TC-TOPIC-21: /profile/download/process → no exception, no callback."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    payload = {
        "version": "1.0",
        "params": {
            "fileId": "log-001",
            "content": "compressed log data...",
        }
    }
    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-001/profile/download/process",
        json.dumps(payload).encode()
    ))
    assert len(results) == 0