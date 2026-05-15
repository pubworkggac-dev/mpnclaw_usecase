"""MQTT client with multi-topic subscription and exponential backoff reconnection."""
import asyncio
import json
import logging
import random
import time
import threading
from typing import Optional, Any
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from src.config import Config

logger = logging.getLogger(__name__)


class MqttClient:
    """Manages MQTT connection with auto-reconnect and multi-topic subscription."""

    def __init__(self, config: Config, on_message_callback=None, on_command_reply_callback=None):
        self.config = config
        self.on_message_callback = on_message_callback
        self.on_command_reply_callback = on_command_reply_callback
        self._running = False
        self._client: Optional[mqtt.Client] = None
        self._connect_lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._create_client()

    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the main asyncio event loop (used for scheduling reply processing)."""
        self._loop = loop

    def _create_client(self):
        """Create and configure the MQTT client."""
        cid = self.config.mqtt.client_id
        clean = self.config.mqtt.clean_session

        try:
            self._client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=cid,
                clean_session=clean,
            )
        except TypeError:
            self._client = mqtt.Client(client_id=cid, clean_session=clean)

        # Configure callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Set username/password if configured
        if self.config.mqtt.username:
            self._client.username_pw_set(
                self.config.mqtt.username,
                self.config.mqtt.password,
            )

        # Set will message
        self._client.will_set(
            topic="bridge/status",
            payload='{"status": "offline"}',
            qos=1,
            retain=True,
        )

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Handle connection established."""
        if rc == 0:
            logger.info(f"Connected to MQTT broker: {self.config.mqtt.broker}")
            self._subscribe_topics()
            # Publish online status
            client.publish("bridge/status", '{"status": "online"}', qos=1, retain=True)
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Handle disconnection."""
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect (rc={rc}), will auto-reconnect")
        else:
            logger.info("MQTT disconnected gracefully")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message.

        Telemetry messages -> on_message_callback (InfluxDB writer).
        Command reply messages (_reply topics) -> schedule on main event loop.
        """
        topic = msg.topic
        if self._is_command_reply_topic(topic):
            self._schedule_reply_processing(topic, msg.payload)
        else:
            from src.mqtt.handler import create_message_handler
            if self.on_message_callback:
                handler = create_message_handler(self.on_message_callback)
                handler(client, userdata, msg)

    def _is_command_reply_topic(self, topic: str) -> bool:
        return topic.endswith("_reply")

    def _schedule_reply_processing(self, topic: str, payload_bytes: bytes):
        """Parse reply payload and schedule on_command_reply on the main event loop."""
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
            message_id = payload.get("id", "")
            if not message_id:
                logger.error(f"Command reply missing 'id' field, topic={topic}")
                return
            logger.info(f"Command reply received: message_id={message_id}, topic={topic}")
            if self._loop is not None:
                from src.api.routes import on_command_reply
                asyncio.run_coroutine_threadsafe(
                    on_command_reply(message_id, payload),
                    self._loop,
                )
        except Exception as e:
            logger.error(f"Command reply handler error, topic={topic}: {e}")

    def subscribe_topic(self, topic: str, qos: int = 1) -> bool:
        """Dynamically subscribe to a topic. Thread-safe."""
        try:
            with self._connect_lock:
                if self._client is None:
                    logger.error("MQTT client not initialized")
                    return False
            result = self._client.subscribe(topic, qos)
            logger.info(f"Dynamic subscribe: {topic} (QoS {qos}, result={result})")
            return result[0] == 0
        except Exception as e:
            logger.error(f"Failed to subscribe {topic}: {e}")
            return False

    def unsubscribe_topic(self, topic: str) -> bool:
        """Dynamically unsubscribe from a topic. Thread-safe."""
        try:
            with self._connect_lock:
                if self._client is None:
                    logger.error("MQTT client not initialized")
                    return False
            result = self._client.unsubscribe(topic)
            logger.info(f"Dynamic unsubscribe: {topic} (result={result})")
            return result[0] == 0
        except Exception as e:
            logger.error(f"Failed to unsubscribe {topic}: {e}")
            return False

    def _subscribe_topics(self):
        """Subscribe to configured topics with QoS."""
        for topic in self.config.mqtt.topics:
            qos = self._derive_qos_for_topic(topic)
            result = self._client.subscribe(topic, qos)
            logger.info(f"Subscribed to {topic} with QoS {qos} (result={result})")

    def _derive_qos_for_topic(self, topic: str) -> int:
        """Derive QoS for a topic based on its purpose."""
        if "/property/" in topic:
            return self.config.mqtt.qos.get("property", 1)
        elif "/service/" in topic:
            if topic.endswith("_reply"):
                return self.config.mqtt.qos.get("service_reply", 1)
            return self.config.mqtt.qos.get("service", 1)
        elif "/ota/upgrade" in topic:
            if "/process" in topic:
                return self.config.mqtt.qos.get("ota_upgrade_process", 1)
            return self.config.mqtt.qos.get("ota_upgrade", 1)
        elif "/ota/get/reply" in topic:
            return self.config.mqtt.qos.get("ota_get_reply", 1)
        elif "/profile/upgrade" in topic:
            if "/process" in topic:
                return self.config.mqtt.qos.get("profile_upgrade_process", 1)
            return self.config.mqtt.qos.get("profile_upgrade", 1)
        elif "/profile/get/reply" in topic:
            return self.config.mqtt.qos.get("profile_get_reply", 1)
        elif "/profile/download" in topic:
            if "/process" in topic:
                return self.config.mqtt.qos.get("profile_download_process", 1)
            return self.config.mqtt.qos.get("profile_download", 1)
        return 1  # Default QoS

    def start(self):
        """Start the MQTT client in a background thread with exponential backoff."""
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True, name="mqtt-client")
        thread.start()
        logger.info("MQTT client started in background thread")

    def _run_loop(self):
        """Connection loop with exponential backoff."""
        attempt = 0
        base_delay = 1.0
        max_delay = 60.0

        while self._running:
            try:
                host, port = self._parse_broker(self.config.mqtt.broker)
                self._client.connect(
                    host,
                    port=port,
                    keepalive=self.config.mqtt.keepalive,
                )
                attempt = 0
                self._client.loop_forever()
            except Exception as e:
                attempt += 1
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                delay *= 0.5 + random.random()
                logger.warning(
                    f"MQTT connection failed (attempt {attempt}): {e}. "
                    f"Reconnecting in {delay:.1f}s..."
                )
                time.sleep(delay)

    @staticmethod
    def _parse_broker(broker: str) -> tuple[str, int]:
        """Parse MQTT broker from host/host:port/tcp://host:port formats."""
        broker = broker.strip()
        if "://" in broker:
            parsed = urlparse(broker)
            host = parsed.hostname or broker
            port = parsed.port or 1883
            return host, port

        # Support plain host:port without URL scheme.
        if ":" in broker:
            host, port_str = broker.rsplit(":", 1)
            if port_str.isdigit():
                return host, int(port_str)

        return broker, 1883

    def stop(self):
        """Stop the MQTT client gracefully."""
        self._running = False
        if self._client:
            self._client.disconnect()
            self._client.loop_stop()
        logger.info("MQTT client stopped")

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected to the broker."""
        return self._client is not None and self._client.is_connected()

    def publish(self, topic: str, payload: str, qos: int = 1) -> bool:
        """Publish a message to an MQTT topic.

        Args:
            topic: MQTT topic to publish to
            payload: JSON string payload
            qos: Quality of service level (0, 1, or 2)

        Returns:
            True if publish was successful, False otherwise
        """
        if not self._client or not self._client.is_connected():
            logger.error("Cannot publish: MQTT client not connected")
            return False
        try:
            result = self._client.publish(topic, payload, qos)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Publish failed to {topic}: {mqtt.error_string(result.rc)}")
                return False
            logger.info(f"Published to {topic} (QoS={qos}, rc={result.rc})")
            return True
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False
