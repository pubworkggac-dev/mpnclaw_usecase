"""Tests for Pydantic data models."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_telemetry_message_minimal():
    """Test TelemetryMessage with minimal fields."""
    from src.models.telemetry import TelemetryMessage
    m = TelemetryMessage(device_id="sensor-001", value=25.5)
    assert m.device_id == "sensor-001"
    assert m.value == 25.5
    assert m.sensor_type == "unknown"
    assert m.location is None

def test_telemetry_message_full():
    """Test TelemetryMessage with all fields."""
    from src.models.telemetry import TelemetryMessage
    m = TelemetryMessage(
        device_id="sensor-001",
        sensor_type="temperature",
        location="building-a-room-101",
        value=25.5,
        unit="celsius",
        timestamp=1672531200000,
    )
    assert m.model_dump()["device_id"] == "sensor-001"
    assert m.value == 25.5
    assert m.timestamp == 1672531200000

def test_device_status():
    """Test DeviceStatus model."""
    from src.models.telemetry import DeviceStatus
    s = DeviceStatus(device_id="sensor-001", status="online")
    assert s.status == "online"

def test_device_status_invalid():
    """Test DeviceStatus rejects invalid status."""
    from src.models.telemetry import DeviceStatus
    import pydantic
    try:
        DeviceStatus(device_id="test", status="invalid_status")
        assert False, "Should have raised validation error"
    except pydantic.ValidationError:
        pass

def test_device_info():
    """Test DeviceInfo model."""
    from src.models.telemetry import DeviceInfo
    d = DeviceInfo(device_id="sensor-001", last_value=25.5)
    assert d.device_id == "sensor-001"
    assert d.last_value == 25.5