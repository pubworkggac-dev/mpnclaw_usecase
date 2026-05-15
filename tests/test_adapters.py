"""Unit tests for MQTT-InfluxDB Bridge format adapters."""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeMessage:
    """Minimal mock for MQTT message."""
    def __init__(self, topic, payload_bytes):
        self.topic = topic
        self.payload = payload_bytes


# =============================================================================
# SimpleAdapter tests
# =============================================================================

def test_simple_adapter_detect():
    """TC-ADAPTER-01: SimpleAdapter.parse — valid complete payload."""
    from src.adapters.simple import SimpleAdapter
    from src.models.telemetry import TelemetryMessage

    adapter = SimpleAdapter()

    payload = {
        "device_id": "sensor-001",
        "sensor_type": "temperature",
        "value": 25.5,
        "unit": "celsius",
        "location": "room-101"
    }
    result = adapter.parse("devices/sensor-001/telemetry", payload)

    assert isinstance(result, TelemetryMessage)
    assert result.device_id == "sensor-001"
    assert result.sensor_type == "temperature"
    assert result.value == 25.5
    assert result.unit == "celsius"
    assert result.location == "room-101"


def test_simple_adapter_required_fields_only():
    """TC-ADAPTER-02: SimpleAdapter.parse — only required fields."""
    from src.adapters.simple import SimpleAdapter
    from src.models.telemetry import TelemetryMessage

    adapter = SimpleAdapter()

    payload = {"device_id": "sensor-002", "value": 42.0}
    result = adapter.parse("devices/sensor-002/telemetry", payload)

    assert isinstance(result, TelemetryMessage)
    assert result.device_id == "sensor-002"
    assert result.value == 42.0
    assert result.sensor_type == "unknown"  # default
    assert result.location is None
    assert result.unit is None


def test_simple_adapter_empty_device_id():
    """TC-ADAPTER-03: SimpleAdapter.parse — empty device_id returns None."""
    from src.adapters.simple import SimpleAdapter

    adapter = SimpleAdapter()

    payload = {"device_id": "", "value": 1.0}
    result = adapter.parse("devices//telemetry", payload)

    assert result is None


def test_simple_adapter_detect_valid():
    """SimpleAdapter.detect — returns True when device_id and value present."""
    from src.adapters.simple import SimpleAdapter

    adapter = SimpleAdapter()
    assert adapter.detect("devices/test/telemetry", {"device_id": "x", "value": 1}) is True


def test_simple_adapter_detect_missing_value():
    """SimpleAdapter.detect — returns False when value missing."""
    from src.adapters.simple import SimpleAdapter

    adapter = SimpleAdapter()
    assert adapter.detect("devices/test/telemetry", {"device_id": "x"}) is False


def test_simple_adapter_detect_missing_device_id():
    """SimpleAdapter.detect — returns False when device_id missing."""
    from src.adapters.simple import SimpleAdapter

    adapter = SimpleAdapter()
    assert adapter.detect("devices/test/telemetry", {"value": 1}) is False


def test_simple_adapter_build_command_topic():
    """TC-ADAPTER-10: SimpleAdapter.build_command_topic — output format correct."""
    from src.adapters.simple import SimpleAdapter

    adapter = SimpleAdapter()
    topic = adapter.build_command_topic("pk-123", "dev-abc", "reboot")
    assert topic == "devices/dev-abc/command/reboot"


def test_simple_adapter_build_command_payload():
    """TC-ADAPTER-10: SimpleAdapter.build_command_payload — output format correct."""
    from src.adapters.simple import SimpleAdapter

    adapter = SimpleAdapter()
    payload = adapter.build_command_payload("reboot", {"delay": 5}, "msg-001")

    assert payload["command"] == "reboot"
    assert payload["params"] == {"delay": 5}
    assert payload["id"] == "msg-001"


def test_simple_adapter_build_command_payload_auto_id():
    """SimpleAdapter.build_command_payload — auto-generates id when None."""
    from src.adapters.simple import SimpleAdapter

    adapter = SimpleAdapter()
    payload = adapter.build_command_payload("reboot", {}, None)

    assert payload["id"] == "auto-generated"


# =============================================================================
# JiujingyunAdapter tests
# =============================================================================

def test_jiujingyun_adapter_parse_property_post():
    """TC-ADAPTER-04: JiujingyunAdapter.parse — thing.property.post with DeviceID.value."""
    from src.adapters.jiujingyun import JiujingyunAdapter
    from src.models.telemetry import TelemetryMessage

    adapter = JiujingyunAdapter()

    payload = {
        "id": "f47ac10b-58cc-4372-a567-0e02b2d3f479",
        "version": "1.0",
        "params": {
            "DeviceID": {"value": "SN-001-ABCD"},
            "MobileNetwork1": {"value": {"Status": 1, "RSRP": "-75"}},
            "CPU": {"value": "0.45"},
            "UseMemory": {"value": "0.62"}
        },
        "method": "thing.property.post"
    }
    result = adapter.parse("/system/test-product/test-device/thing/property/post", payload)

    assert isinstance(result, TelemetryMessage)
    assert result.device_id == "SN-001-ABCD"
    assert result.sensor_type == "property"
    assert result.value == 0.45
    assert result.unit == "percent"
    assert result.location is not None
    assert "MobileNetwork1" in result.location


def test_jiujingyun_adapter_parse_service_command():
    """TC-ADAPTER-05: JiujingyunAdapter.parse — thing.service.* command, device from topic."""
    from src.adapters.jiujingyun import JiujingyunAdapter
    from src.models.telemetry import TelemetryMessage

    adapter = JiujingyunAdapter()

    payload = {
        "id": "cmd-12345",
        "version": "1.0.0",
        "params": {
            "DeviceName": "OfficeRouter",
            "NtpSwitch": "1"
        },
        "method": "thing.service.SetDeviceName"
    }
    result = adapter.parse("/system/test-product/test-device-001/thing/service/SetDeviceName", payload)

    assert isinstance(result, TelemetryMessage)
    assert result.device_id == "test-device-001"
    assert result.sensor_type == "service"


def test_jiujingyun_adapter_parse_no_device_id_in_params():
    """TC-ADAPTER-06: JiujingyunAdapter.parse — no DeviceID, device_id from topic."""
    from src.adapters.jiujingyun import JiujingyunAdapter
    from src.models.telemetry import TelemetryMessage

    adapter = JiujingyunAdapter()

    payload = {
        "params": {"CPU": {"value": "0.80"}},
        "method": "thing.property.post"
    }
    result = adapter.parse("/system/prod-xyz/device-abc/thing/property/post", payload)

    assert isinstance(result, TelemetryMessage)
    assert result.device_id == "device-abc"
    assert result.sensor_type == "property"


def test_jiujingyun_adapter_extract_primary_value_cpu():
    """TC-ADAPTER-07: JiujingyunAdapter._extract_primary_value — CPU extracted as float."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    value, unit = adapter._extract_primary_value({"CPU": {"value": "0.75"}})

    assert value == 0.75
    assert unit == "percent"


def test_jiujingyun_adapter_extract_primary_value_memory():
    """JiujingyunAdapter._extract_primary_value — UseMemory extracted as float."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    value, unit = adapter._extract_primary_value({"UseMemory": {"value": "0.62"}})

    assert value == 0.62
    assert unit == "percent"


def test_jiujingyun_adapter_extract_primary_value_disk():
    """JiujingyunAdapter._extract_primary_value — DiskUsage extracted as float."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    value, unit = adapter._extract_primary_value({"DiskUsage": {"value": "0.85"}})

    assert value == 0.85
    assert unit == "percent"


def test_jiujingyun_adapter_extract_primary_value_temperature():
    """JiujingyunAdapter._extract_primary_value — ModuleTemperature extracted with no unit."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    value, unit = adapter._extract_primary_value({"ModuleTemperature": {"value": "45.5"}})

    assert value == 45.5
    assert unit is None


def test_jiujingyun_adapter_extract_primary_value_missing():
    """JiujingyunAdapter._extract_primary_value — no recognized key returns 0.0."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    value, unit = adapter._extract_primary_value({"UnknownKey": {"value": "1.0"}})

    assert value == 0.0
    assert unit is None


def test_jiujingyun_adapter_extract_device_id_from_params():
    """JiujingyunAdapter._extract_device_id — extracts from DeviceID.value dict."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    device_id = adapter._extract_device_id({"DeviceID": {"value": "DEV-123"}})

    assert device_id == "DEV-123"


def test_jiujingyun_adapter_extract_device_id_not_dict():
    """JiujingyunAdapter._extract_device_id — returns None when DeviceID not dict."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    device_id = adapter._extract_device_id({"DeviceID": "just-a-string"})

    assert device_id is None


def test_jiujingyun_adapter_extract_device_from_topic():
    """JiujingyunAdapter._extract_device_from_topic — extracts device from /system/{product}/{device}/..."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    device_id = adapter._extract_device_from_topic("/system/my-product/my-device/thing/property/post")

    assert device_id == "my-device"


def test_jiujingyun_adapter_extract_device_from_topic_short():
    """JiujingyunAdapter._extract_device_from_topic — returns None for short topic."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    device_id = adapter._extract_device_from_topic("/system/prod/thing")

    assert device_id is None


def test_jiujingyun_adapter_derive_sensor_type_property():
    """JiujingyunAdapter._derive_sensor_type — returns property for thing.property.*."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    assert adapter._derive_sensor_type("thing.property.post") == "property"


def test_jiujingyun_adapter_derive_sensor_type_service():
    """JiujingyunAdapter._derive_sensor_type — returns service for thing.service.*."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    assert adapter._derive_sensor_type("thing.service.Reboot") == "service"


def test_jiujingyun_adapter_derive_sensor_type_unknown():
    """JiujingyunAdapter._derive_sensor_type — returns unknown for other methods."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    assert adapter._derive_sensor_type("thing.other.method") == "unknown"


def test_jiujingyun_adapter_detect_valid():
    """JiujingyunAdapter.detect — returns True for thing.property.post."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    assert adapter.detect("/topic", {"method": "thing.property.post"}) is True


def test_jiujingyun_adapter_detect_service():
    """JiujingyunAdapter.detect — returns True for thing.service.*."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    assert adapter.detect("/topic", {"method": "thing.service.Reboot"}) is True


def test_jiujingyun_adapter_detect_false():
    """JiujingyunAdapter.detect — returns False when method doesn't start with thing."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    assert adapter.detect("/topic", {"method": "other.method"}) is False
    assert adapter.detect("/topic", {"method": "thing.property"}) is True


def test_jiujingyun_adapter_build_command_topic():
    """TC-ADAPTER-11: JiujingyunAdapter.build_command_topic — output format correct."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    topic = adapter.build_command_topic("pk-123", "dev-abc", "reboot")

    assert topic == "/system/pk-123/dev-abc/thing/service/reboot"


def test_jiujingyun_adapter_build_command_payload():
    """TC-ADAPTER-11: JiujingyunAdapter.build_command_payload — output format correct."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    payload = adapter.build_command_payload("Reboot", {"delay": 5}, "msg-002")

    assert payload["id"] == "msg-002"
    assert payload["version"] == "1.0.0"
    assert payload["params"] == {"delay": 5}
    assert payload["method"] == "thing.service.Reboot"


def test_jiujingyun_adapter_build_command_payload_auto_id():
    """JiujingyunAdapter.build_command_payload — auto-generates id when None."""
    from src.adapters.jiujingyun import JiujingyunAdapter

    adapter = JiujingyunAdapter()
    payload = adapter.build_command_payload("Reboot", {}, None)

    assert payload["id"] == "auto-generated"


# =============================================================================
# FormatRouter tests
# =============================================================================

def test_format_router_jiujingyun_wins_when_both_match():
    """TC-ADAPTER-08: Payload matching BOTH adapters — Jiujingyun wins (registered first)."""
    from src.adapters.router import FormatRouter
    from src.adapters.jiujingyun import JiujingyunAdapter
    from src.adapters.simple import SimpleAdapter
    from src.models.telemetry import TelemetryMessage

    router = FormatRouter()
    router.register(JiujingyunAdapter())
    router.register(SimpleAdapter())

    # Payload has both device_id+value AND method.startswith("thing.")
    payload = {
        "device_id": "should-be-simple",
        "value": 99.0,
        "method": "thing.property.post",
        "params": {"DeviceID": {"value": "jiujingyun-device"}}
    }
    result = router.parse("/system/test-prod/test-device/thing/property/post", payload)

    assert isinstance(result, TelemetryMessage)
    # Jiujingyun wins because it's registered first
    assert result.device_id == "jiujingyun-device"


def test_format_router_simple_when_jiujingyun_not_matched():
    """FormatRouter — SimpleAdapter used when Jiujingyun doesn't match."""
    from src.adapters.router import FormatRouter
    from src.adapters.jiujingyun import JiujingyunAdapter
    from src.adapters.simple import SimpleAdapter

    router = FormatRouter()
    router.register(JiujingyunAdapter())
    router.register(SimpleAdapter())

    # Simple format — no method field
    payload = {"device_id": "simple-device", "value": 55.5}
    result = router.parse("devices/simple-device/telemetry", payload)

    assert result is not None
    assert result.device_id == "simple-device"
    assert result.value == 55.5


def test_format_router_unknown_format_returns_none():
    """TC-ADAPTER-09: Unknown format — parse returns None."""
    from src.adapters.router import FormatRouter
    from src.adapters.simple import SimpleAdapter

    router = FormatRouter()
    router.register(SimpleAdapter())

    # Neither adapter matches
    payload = {"some_field": "some_value"}
    result = router.parse("unknown/topic", payload)

    assert result is None


def test_format_router_detect_returns_adapter():
    """FormatRouter.detect — returns first matching adapter."""
    from src.adapters.router import FormatRouter
    from src.adapters.simple import SimpleAdapter

    router = FormatRouter()
    router.register(SimpleAdapter())

    adapter = router.detect("devices/x/telemetry", {"device_id": "x", "value": 1})
    assert adapter is not None
    assert adapter.format_id == "simple"


def test_format_router_detect_returns_none():
    """FormatRouter.detect — returns None when no adapter matches."""
    from src.adapters.router import FormatRouter
    from src.adapters.simple import SimpleAdapter

    router = FormatRouter()
    router.register(SimpleAdapter())

    adapter = router.detect("unknown/topic", {"unknown": "data"})
    assert adapter is None


def test_format_router_registration_order():
    """FormatRouter — later registered adapter used when first doesn't match."""
    from src.adapters.router import FormatRouter
    from src.adapters.simple import SimpleAdapter
    from src.adapters.jiujingyun import JiujingyunAdapter

    # Register Simple first, Jiujingyun second
    router = FormatRouter()
    router.register(SimpleAdapter())
    router.register(JiujingyunAdapter())

    # Jiujingyun format (no device_id field) — should use Jiujingyun
    payload = {"method": "thing.service.echo", "params": {}}
    result = router.parse("/system/p/d/thing/service/echo", payload)

    assert result is not None
    assert result.sensor_type == "service"