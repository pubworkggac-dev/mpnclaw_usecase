"""Tests for Line Protocol encoder."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_encode_single_message():
    """Test encoding a single telemetry message."""
    from src.lineprotocol import encode_line_protocol
    from src.models.telemetry import TelemetryMessage

    m = TelemetryMessage(
        device_id="sensor-001",
        sensor_type="temperature",
        value=25.5,
        unit="celsius",
        timestamp=1672531200000,
    )

    lp = encode_line_protocol(m)
    assert "device_telemetry" in lp
    assert "device_id=sensor-001" in lp
    assert "sensor_type=temperature" in lp
    assert "value=25.5" in lp
    assert "unit=\"celsius\"" in lp
    assert "1672531200000000000" in lp  # ns timestamp

def test_encode_escape():
    """Test tag value escaping for special characters."""
    from src.lineprotocol import encode_line_protocol
    from src.models.telemetry import TelemetryMessage

    m = TelemetryMessage(
        device_id="sensor,with=comma and space",
        value=1.0,
        timestamp=1000,
    )

    lp = encode_line_protocol(m)
    assert "device_id=sensor\\,with\\=comma\\ and\\ space" in lp

def test_encode_batch():
    """Test batch encoding of multiple messages."""
    from src.lineprotocol import encode_batch
    from src.models.telemetry import TelemetryMessage

    msgs = [
        TelemetryMessage(device_id="s1", value=1.0, timestamp=1000),
        TelemetryMessage(device_id="s2", value=2.0, timestamp=2000),
        TelemetryMessage(device_id="s3", value=3.0, timestamp=3000),
    ]

    batch = encode_batch(msgs)
    lines = batch.split("\n")
    assert len(lines) == 3
    for i, line in enumerate(lines):
        assert f"device_id=s{i+1}" in line

def test_no_timestamp():
    """Test encoding without timestamp uses current time."""
    from src.lineprotocol import encode_line_protocol
    from src.models.telemetry import TelemetryMessage
    from datetime import datetime

    m = TelemetryMessage(device_id="s1", value=1.0)
    lp = encode_line_protocol(m)
    # Should have a timestamp at the end (not "None")
    parts = lp.split(" ")
    assert len(parts) == 3
    assert parts[2].isdigit()