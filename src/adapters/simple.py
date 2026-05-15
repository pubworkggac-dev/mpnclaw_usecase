from src.models.telemetry import TelemetryMessage


class SimpleAdapter:
    format_id = "simple"

    def detect(self, topic: str, payload: dict) -> bool:
        return "device_id" in payload and "value" in payload

    def parse(self, topic: str, payload: dict) -> TelemetryMessage | None:
        device_id = payload.get("device_id", "")
        if not device_id:
            return None
        return TelemetryMessage(
            device_id=device_id,
            sensor_type=payload.get("sensor_type", "unknown"),
            location=payload.get("location"),
            value=float(payload.get("value", 0)),
            unit=payload.get("unit"),
            timestamp=payload.get("timestamp"),
        )

    def build_command_topic(
        self, product_key: str, device_key: str, service_name: str
    ) -> str:
        return f"devices/{device_key}/command/{service_name}"

    def build_command_payload(
        self, service_name: str, params: dict, message_id: str | None = None
    ) -> dict:
        msg_id = message_id or "auto-generated"
        return {
            "command": service_name,
            "params": params,
            "id": msg_id,
        }