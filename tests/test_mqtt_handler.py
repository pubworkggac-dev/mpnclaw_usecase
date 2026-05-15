"""Tests for MQTT message handler."""
import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

class FakeMessage:
    """Minimal mock for MQTT message."""
    def __init__(self, topic, payload_bytes):
        self.topic = topic
        self.payload = payload_bytes

def test_parse_valid_telemetry():
    """Test parsing valid JSON telemetry."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    payload = json.dumps({
        "device_id": "sensor-001",
        "sensor_type": "temperature",
        "value": 25.5,
        "unit": "celsius",
        "timestamp": 1672531200000,
    })

    handler(None, None, FakeMessage("devices/sensor-001/telemetry", payload.encode()))

    assert len(results) == 1
    assert results[0].device_id == "sensor-001"
    assert results[0].value == 25.5

def test_parse_invalid_json():
    """Test that invalid JSON doesn't crash the handler."""
    from src.mqtt.handler import create_message_handler

    called = []
    def callback(telemetry):
        called.append(telemetry)

    handler = create_message_handler(callback)
    # Invalid JSON
    handler(None, None, FakeMessage("devices/test/telemetry", b"not-json"))

    assert len(called) == 0  # Should not call callback on parse failure

def test_parse_partial_data():
    """Test parsing telemetry with missing optional fields."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)
    # Minimal JSON
    payload = json.dumps({"device_id": "s1", "value": 42.0})
    handler(None, None, FakeMessage("devices/s1/telemetry", payload.encode()))

    assert len(results) == 1
    assert results[0].device_id == "s1"
    assert results[0].value == 42.0
    assert results[0].sensor_type == "unknown"  # default


# =============================================================================
# RED tests for jiujingyun protocol support
# =============================================================================

def test_parse_jiujingyun_property_post():
    """Test parsing jiujingyun property post format (thing.property.post)."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    # Jiujingyun property post payload
    payload = json.dumps({
        "id": "f47ac10b-58cc-4372-a567-0e02b2d3f479",
        "version": "1.0",
        "sys": {"ack": 0},
        "params": {
            "DeviceID": {"value": "SN-001-ABCD"},
            "MobileNetwork1": {
                "value": {
                    "Status": 1,
                    "CommunityID": "0x1234ABCD",
                    "RSRP": "-75",
                    "IPV4": "10.0.1.100"
                }
            },
            "CPU": {"value": "0.45"},
            "UseMemory": {"value": "0.62"}
        },
        "method": "thing.property.post"
    })

    handler(None, None, FakeMessage(
        "/system/test-product/test-device-001/thing/property/post",
        payload.encode()
    ))

    assert len(results) == 1
    assert results[0].device_id == "SN-001-ABCD"
    assert results[0].sensor_type == "property"
    assert "MobileNetwork1" in results[0].location


def test_parse_jiujingyun_mobile_network_fields():
    """Test that MobileNetwork1 nested fields (RSRP, Status, IPV4) are extracted."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    # Payload with MobileNetwork1 details
    payload = json.dumps({
        "id": "test-id-002",
        "version": "1.0",
        "sys": {"ack": 0},
        "params": {
            "DeviceID": {"value": "cpe-router-001"},
            "MobileNetwork1": {
                "value": {
                    "Status": 1,
                    "RSRP": "-85",
                    "IPV4": "192.168.1.100",
                    "BAND": "B3"
                }
            },
            "MobileNetwork2": {
                "value": {
                    "Status": 0,
                    "RSRP": "",
                    "IPV4": ""
                }
            }
        },
        "method": "thing.property.post"
    })

    handler(None, None, FakeMessage(
        "/system/my-product/my-device/thing/property/post",
        payload.encode()
    ))

    assert len(results) == 1
    t = results[0]
    assert t.device_id == "cpe-router-001"
    # Verify that MobileNetwork1 data was extracted as extra fields
    # The handler should store the nested data in location or similar field
    assert t.location is not None


def test_parse_jiujingyun_service_command():
    """Test parsing jiujingyun service command (thing.service.*)."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    # Service command payload (device receives command from cloud)
    payload = json.dumps({
        "id": "cmd-12345",
        "version": "1.0.0",
        "params": {
            "DeviceName": "OfficeRouter",
            "NtpSwitch": "1",
            "NtpServer1": "pool.ntp.org"
        },
        "method": "thing.service.SetDeviceName"
    })

    handler(None, None, FakeMessage(
        "/system/test-product/test-device-001/thing/service/SetDeviceName",
        payload.encode()
    ))

    # Service commands should also be parsed as telemetry
    assert len(results) == 1
    assert results[0].device_id == "test-device-001"
    assert results[0].sensor_type == "service"


def test_backward_compat_simple_format():
    """Test that old simple format still works after jiujingyun support added."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)

    handler = create_message_handler(callback)

    # Old simple format
    payload = json.dumps({
        "device_id": "legacy-sensor-01",
        "sensor_type": "temperature",
        "value": 25.5,
        "unit": "celsius"
    })

    handler(None, None, FakeMessage("devices/legacy-sensor-01/telemetry", payload.encode()))

    assert len(results) == 1
    assert results[0].device_id == "legacy-sensor-01"
    assert results[0].value == 25.5


# =============================================================================
# Topic routing tests (TC-TOPIC-17 to TC-TOPIC-21)
# =============================================================================

def test_parse_jiujingyun_property_post_topic():
    """TC-TOPIC-17: /system/pk/dk/thing/property/post → JiujingyunAdapter.parse()."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)
    handler = create_message_handler(callback)

    payload = json.dumps({
        "id": "msg-prop-001",
        "version": "1.0",
        "params": {
            "DeviceID": {"value": "dev-prop-001"},
            "CPU": {"value": "0.50"},
        },
        "method": "thing.property.post"
    })
    handler(None, None, FakeMessage(
        "/system/my-product/device-prop-001/thing/property/post",
        payload.encode()
    ))

    assert len(results) == 1
    assert results[0].device_id == "dev-prop-001"
    assert results[0].sensor_type == "property"


def test_parse_jiujingyun_service_topic():
    """TC-TOPIC-18: /system/pk/dk/thing/service/Reboot → JiujingyunAdapter.parse()."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)
    handler = create_message_handler(callback)

    payload = json.dumps({
        "id": "msg-svc-001",
        "version": "1.0.0",
        "params": {"Delay": 5},
        "method": "thing.service.Reboot"
    })
    handler(None, None, FakeMessage(
        "/system/my-product/device-svc-001/thing/service/Reboot",
        payload.encode()
    ))

    assert len(results) == 1
    assert results[0].device_id == "device-svc-001"
    assert results[0].sensor_type == "service"


def test_ota_upgrade_topic_silent_pass():
    """TC-TOPIC-20: /ota/upgrade message → no exception, no callback."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)
    handler = create_message_handler(callback)

    payload = json.dumps({
        "version": "1.0",
        "params": {
            "downloadUrl": "http://example.com/fw.bin",
            "version": "2.1.0",
        }
    })
    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-001/ota/upgrade",
        payload.encode()
    ))
    assert len(results) == 0


def test_profile_download_process_topic_silent_pass():
    """TC-TOPIC-21: /profile/download/process → no exception, no callback."""
    from src.mqtt.handler import create_message_handler
    from src.models.telemetry import TelemetryMessage

    results = []
    def callback(telemetry: TelemetryMessage):
        results.append(telemetry)
    handler = create_message_handler(callback)

    payload = json.dumps({
        "version": "1.0",
        "params": {
            "fileId": "log-001",
            "content": "compressed log data...",
        }
    })
    handler(None, None, FakeMessage(
        "/system/jiujing_cpe/cpe-001/profile/download/process",
        payload.encode()
    ))
    assert len(results) == 0