"""InfluxDB v2 query executor (HTTP Flux API)."""
import logging
import csv
import io
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.config import Config

logger = logging.getLogger(__name__)

class InfluxDBQuery:
    """Execute queries against InfluxDB v2."""

    def __init__(self, config: Config):
        self.config = config

    def connect(self):
        logger.info("InfluxDB query running in v2 mode (HTTP Flux)")

    def query_sql(self, sql: str, database: str | None = None) -> dict:
        """Execute a SQL query and return structured results.

        Returns:
            dict with:
                - success: bool
                - data: list of row dicts
                - meta: column info (or None)
                - error: error message (or None)
        """
        return {
            "success": False,
            "data": [],
            "error": "Raw SQL endpoint is not available in InfluxDB v2 mode. Use /api/v1/devices or telemetry APIs.",
        }

    def get_devices(self) -> list[dict]:
        """Get list of all unique device IDs."""
        flux = (
            f'from(bucket: "{self.config.influxdb.database}") '
            f"|> range(start: -30d) "
            f'|> filter(fn: (r) => r._measurement == "device_telemetry") '
            f'|> keep(columns: ["device_id"]) '
            f'|> group() '
            f'|> distinct(column: "device_id") '
            f'|> sort(columns: ["device_id"])'
        )
        result = self._query_flux_v2(flux)
        if not result["success"]:
            return []
        devices = []
        for row in result["data"]:
            device_id = row.get("device_id") or row.get("_value")
            if device_id:
                devices.append({"device_id": device_id})
        return devices

    def get_device_telemetry(
        self, device_id: str, start: str = "-1h", end: str = "now", limit: int = 100
    ) -> dict:
        """Get telemetry data for a specific device.

        Args:
            device_id: Device identifier
            start: Start time (RFC3339 or relative like '-1h')
            end: End time ('now' or RFC3339)
            limit: Max rows
        """
        flux = (
            f'from(bucket: "{self.config.influxdb.database}") '
            f"|> range(start: {start}) "
            f'|> filter(fn: (r) => r._measurement == "device_telemetry") '
            f'|> filter(fn: (r) => r.device_id == "{device_id}") '
            f'|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value") '
            f'|> sort(columns: ["_time"], desc: true) '
            f"|> limit(n: {limit})"
        )
        result = self._query_flux_v2(flux)
        if not result["success"]:
            return result

        data = []
        for row in result["data"]:
            item = {
                "time": row.get("_time"),
                "device_id": row.get("device_id"),
                "sensor_type": row.get("sensor_type"),
                "value": self._to_float(row.get("value")),
                "unit": row.get("unit"),
                "location": row.get("location"),
            }
            data.append(item)

        return {
            "success": True,
            "data": data,
            "meta": {"count": len(data)},
        }

    def close(self):
        return

    @staticmethod
    def _to_float(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _query_flux_v2(self, flux: str) -> dict:
        """Run Flux query against InfluxDB v2 HTTP API and parse CSV response."""
        try:
            base_url = self.config.influxdb.url.rstrip("/")
            query_url = f"{base_url}/api/v2/query?{urlencode({'org': self.config.influxdb.org})}"
            payload = json.dumps({"query": flux, "type": "flux"}).encode("utf-8")

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/csv",
            }
            token = self.config.influxdb.token or ""
            if token:
                headers["Authorization"] = f"Token {token}"

            req = Request(query_url, data=payload, headers=headers, method="POST")
            with urlopen(req, timeout=30) as resp:
                csv_text = resp.read().decode("utf-8", errors="replace")

            rows = []
            reader = csv.DictReader(io.StringIO(csv_text))
            for row in reader:
                # Filter out annotation or empty rows.
                if not row:
                    continue
                if row.get("result", "").startswith("#"):
                    continue
                rows.append(row)

            return {
                "success": True,
                "data": rows,
                "meta": {"count": len(rows)},
            }
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {
                "success": False,
                "data": [],
                "error": str(e),
            }