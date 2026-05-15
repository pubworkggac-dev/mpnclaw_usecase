import json

from src.models.telemetry import TelemetryMessage


class JiujingyunAdapter:
    format_id = "jiujingyun"

    def detect(self, topic: str, payload: dict) -> bool:
        return "method" in payload and str(payload.get("method", "")).startswith("thing.")

    def parse(self, topic: str, payload: dict) -> TelemetryMessage | None:
        method = payload.get("method", "")
        params = payload.get("params", {})
        device_id = self._extract_device_id(params) or self._extract_device_from_topic(topic)
        if not device_id:
            return None
        sensor_type = self._derive_sensor_type(method)
        location = self._extract_location(params)
        value, unit = self._extract_primary_value(params)
        return TelemetryMessage(
            device_id=device_id,
            sensor_type=sensor_type,
            location=location,
            value=value,
            unit=unit,
            timestamp=payload.get("timestamp"),
        )

    def _extract_device_id(self, params: dict) -> str | None:
        device_id_obj = params.get("DeviceID")
        if isinstance(device_id_obj, dict) and "value" in device_id_obj:
            return str(device_id_obj["value"])
        return None

    def _extract_device_from_topic(self, topic: str) -> str | None:
        parts = topic.strip("/").split("/")
        if len(parts) >= 4 and parts[0] == "system":
            return parts[2]
        return None

    def _derive_sensor_type(self, method: str) -> str:
        if ".property." in method:
            return "property"
        if ".service." in method:
            return "service"
        return "unknown"

    def _extract_location(self, params: dict) -> str | None:
        location_fields = {}
        for key in [
            "MobileNetwork1", "MobileNetwork2", "SIMCard1", "SIMCard2",
            "WLAN", "LAN", "WiredPort1Info", "WiredPort2Info"
        ]:
            if key in params:
                location_fields[key] = params[key]
        if location_fields:
            return json.dumps(location_fields)
        return None

    def _extract_primary_value(self, params: dict) -> tuple[float, str | None]:
        for key in ["CPU", "UseMemory", "DiskUsage", "ModuleTemperature"]:
            if key in params and isinstance(params[key], dict):
                val = params[key].get("value")
                if val is not None:
                    try:
                        return float(val), "percent" if key in ["CPU", "UseMemory", "DiskUsage"] else None
                    except (ValueError, TypeError):
                        pass
        return 0.0, None

    def build_command_topic(
        self, product_key: str, device_key: str, service_name: str
    ) -> str:
        return f"/system/{product_key}/{device_key}/thing/service/{service_name}"

    def build_command_payload(
        self, service_name: str, params: dict, message_id: str | None = None
    ) -> dict:
        return {
            "id": message_id or "auto-generated",
            "version": "1.0.0",
            "params": params,
            "method": f"thing.service.{service_name}",
        }