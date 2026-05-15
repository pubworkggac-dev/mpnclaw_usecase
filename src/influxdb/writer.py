"""InfluxDB v2 batch writer with thread-safe queue and periodic flush."""
import logging
import threading
import time
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.config import Config
from src.models.telemetry import TelemetryMessage
from src.lineprotocol import encode_line_protocol

logger = logging.getLogger(__name__)


class InfluxDBWriter:
    """Batcher that collects telemetry and flushes to InfluxDB v2."""

    def __init__(self, config: Config):
        self.config = config
        self._buffer: list[TelemetryMessage] = []
        self._lock = threading.Lock()
        self._flush_event = threading.Event()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_flush = time.time()
        self._write_url = self._build_write_url()
        self._headers = self._build_headers()
        self._connected = False

    def start(self):
        """Start the batch writer background thread."""
        self._running = True
        self._probe_connectivity()
        self._thread = threading.Thread(target=self._flush_loop, daemon=True, name="influxdb-writer")
        self._thread.start()
        logger.info(
            f"InfluxDB writer started: batch_size={self.config.batch.size}, "
            f"flush_interval={self.config.batch.flush_interval}s"
        )

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _build_write_url(self) -> str:
        base_url = self.config.influxdb.url.rstrip("/")
        params = urlencode(
            {
                "org": self.config.influxdb.org,
                "bucket": self.config.influxdb.database,
                "precision": "ns",
            }
        )
        return f"{base_url}/api/v2/write?{params}"

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        token = self.config.influxdb.token or ""
        if token:
            headers["Authorization"] = f"Token {token}"
        return headers

    def _probe_connectivity(self):
        """Ping InfluxDB v2 /health endpoint once during startup."""
        health_url = f"{self.config.influxdb.url.rstrip('/')}/health"
        try:
            req = Request(health_url, method="GET")
            with urlopen(req, timeout=5) as resp:
                self._connected = resp.status == 200
            if self._connected:
                logger.info(f"InfluxDB v2 reachable: {self.config.influxdb.url}")
            else:
                logger.warning("InfluxDB health check returned non-200 status")
        except Exception as e:
            self._connected = False
            logger.warning(f"InfluxDB health check failed: {e}")

    def write(self, msg: TelemetryMessage):
        """Queue a telemetry message for batch writing."""
        with self._lock:
            self._buffer.append(msg)
            if len(self._buffer) >= self.config.batch.size:
                self._flush_event.set()

    def _flush_loop(self):
        while self._running:
            triggered = self._flush_event.wait(timeout=self.config.batch.flush_interval)
            if triggered:
                self._flush_event.clear()
            elapsed = time.time() - self._last_flush
            if elapsed >= self.config.batch.flush_interval:
                self._flush()

    def _flush(self):
        with self._lock:
            if not self._buffer:
                return
            batch = self._buffer
            self._buffer = []
            self._last_flush = time.time()

        try:
            lp_data = "\n".join(encode_line_protocol(msg) for msg in batch)
            req = Request(
                self._write_url,
                data=lp_data.encode("utf-8"),
                headers=self._headers,
                method="POST",
            )
            with urlopen(req, timeout=self.config.batch.timeout) as resp:
                self._connected = 200 <= resp.status < 300
            logger.info(f"Flushed {len(batch)} messages to InfluxDB")
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to flush batch ({len(batch)} msgs): {e}")
            with self._lock:
                self._buffer = batch + self._buffer
                max_buffer = self.config.batch.size * 10
                if len(self._buffer) > max_buffer:
                    dropped = len(self._buffer) - max_buffer
                    self._buffer = self._buffer[-max_buffer:]
                    logger.warning(f"Dropped {dropped} oldest messages (buffer full)")

    @property
    def buffer_size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def stop(self):
        logger.info("Stopping InfluxDB writer...")
        self._running = False
        self._flush_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        self._flush()
        logger.info("InfluxDB writer stopped")