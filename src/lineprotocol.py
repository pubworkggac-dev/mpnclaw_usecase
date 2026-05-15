"""Line Protocol encoder for InfluxDB.

Converts telemetry messages into InfluxDB Line Protocol format.

Format:
    <measurement>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]]
        <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>]

Reference: https://docs.influxdata.com/influxdb/v1/write_protocols/line_protocol_reference/
"""

from datetime import datetime, timezone
from typing import Optional
from src.models.telemetry import TelemetryMessage


def _escape_tag(value: str) -> str:
    """Escape special characters in tag values.

    Commas, equals signs, and spaces must be escaped with backslash.
    """
    result = value.replace('\\', '\\\\')
    result = result.replace(' ', '\\ ')
    result = result.replace(',', '\\,')
    result = result.replace('=', '\\=')
    return result


def _escape_field_string(value: str) -> str:
    """Escape special characters in string field values."""
    result = value.replace('\\', '\\\\')
    result = result.replace('"', '\\"')
    return result


def encode_line_protocol(
    msg: TelemetryMessage,
    measurement: str = "device_telemetry",
) -> str:
    """Encode a TelemetryMessage into Line Protocol format.

    Args:
        msg: Telemetry message to encode
        measurement: InfluxDB measurement name

    Returns:
        Line Protocol string ready for InfluxDB write

    Example output:
        device_telemetry,device_id=sensor-001,sensor_type=temperature value=25.5 1672531200000000000
    """
    # Build tags
    tags = []
    tags.append(f"device_id={_escape_tag(msg.device_id)}")
    if msg.sensor_type:
        tags.append(f"sensor_type={_escape_tag(msg.sensor_type)}")
    if msg.location:
        tags.append(f"location={_escape_tag(msg.location)}")

    # Build fields
    fields = []
    fields.append(f"value={msg.value}")
    if msg.unit:
        fields.append(f"unit=\"{_escape_field_string(msg.unit)}\"")

    # Build timestamp (convert ms to ns)
    if msg.timestamp is not None:
        timestamp_ns = int(msg.timestamp) * 1_000_000
    else:
        timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)

    # Assemble Line Protocol string
    tags_str = ",".join(tags)
    fields_str = ",".join(fields)
    return f"{measurement},{tags_str} {fields_str} {timestamp_ns}"


def encode_batch(
    messages: list[TelemetryMessage],
    measurement: str = "device_telemetry",
) -> str:
    """Encode multiple TelemetryMessages into a batch Line Protocol string.

    Each message is separated by a newline for batch writes.

    Args:
        messages: List of telemetry messages
        measurement: InfluxDB measurement name

    Returns:
        Multi-line Line Protocol string
    """
    lines = [encode_line_protocol(m, measurement) for m in messages]
    return "\n".join(lines)