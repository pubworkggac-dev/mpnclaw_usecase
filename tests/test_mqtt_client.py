"""Tests for MQTT client topic subscription and QoS derivation."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set config path before importing config module
os.environ["CONFIG_PATH"] = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

from unittest.mock import MagicMock, patch


class FakeMQTTClient:
    """Minimal fake paho MQTT client for testing."""
    def __init__(self, connected: bool = True):
        self.subscriptions = []
        self._on_connect = None
        self._on_disconnect = None
        self._on_message = None
        self._connected = connected

    def is_connected(self) -> bool:
        return self._connected

    def connect(self, host, port, keepalive):
        pass

    def disconnect(self):
        pass

    def loop_stop(self):
        pass

    def publish(self, topic, payload, qos=0):
        class Result:
            rc = 0
        return Result()

    def subscribe(self, topic, qos=0):
        self.subscriptions.append((topic, qos))
        return (0, 1)

    def unsubscribe(self, topic):
        self.subscriptions = [(t, q) for (t, q) in self.subscriptions if t != topic]
        return (0, 1)

    def on_connect(self, fn):
        self._on_connect = fn

    def on_disconnect(self, fn):
        self._on_disconnect = fn

    def on_message(self, fn):
        self._on_message = fn

    def will_set(self, **kwargs):
        pass

    def username_pw_set(self, *args, **kwargs):
        pass


# =============================================================================
# QoS derivation tests (TC-TOPIC-05 to TC-TOPIC-16)
# =============================================================================


def test_qos_derive_property_post():
    """TC-TOPIC-05: /thing/property/post → QoS property=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/thing/property/post")
        assert qos == 1
        assert cfg.mqtt.qos.get("property") == 1


def test_qos_derive_service_command():
    """TC-TOPIC-06: /thing/service/Reboot → QoS service=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/thing/service/Reboot")
        assert qos == 1
        assert cfg.mqtt.qos.get("service") == 1


def test_qos_derive_service_reply():
    """TC-TOPIC-07: /thing/service/Reboot_reply → QoS service_reply=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/thing/service/Reboot_reply")
        assert qos == 1
        assert cfg.mqtt.qos.get("service_reply") == 1


def test_qos_derive_ota_upgrade():
    """TC-TOPIC-08: /ota/upgrade → QoS ota_upgrade=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/ota/upgrade")
        assert qos == 1
        assert cfg.mqtt.qos.get("ota_upgrade") == 1


def test_qos_derive_ota_get_reply():
    """TC-TOPIC-09: /ota/get/reply → QoS ota_get_reply=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/ota/get/reply")
        assert qos == 1
        assert cfg.mqtt.qos.get("ota_get_reply") == 1


def test_qos_derive_ota_upgrade_process():
    """TC-TOPIC-10: /ota/upgrade/process → QoS ota_upgrade_process=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/ota/upgrade/process")
        assert qos == 1
        assert cfg.mqtt.qos.get("ota_upgrade_process") == 1


def test_qos_derive_profile_upgrade():
    """TC-TOPIC-11: /profile/upgrade → QoS profile_upgrade=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/profile/upgrade")
        assert qos == 1
        assert cfg.mqtt.qos.get("profile_upgrade") == 1


def test_qos_derive_profile_get_reply():
    """TC-TOPIC-12: /profile/get/reply → QoS profile_get_reply=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/profile/get/reply")
        assert qos == 1
        assert cfg.mqtt.qos.get("profile_get_reply") == 1


def test_qos_derive_profile_upgrade_process():
    """TC-TOPIC-13: /profile/upgrade/process → QoS profile_upgrade_process=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/profile/upgrade/process")
        assert qos == 1
        assert cfg.mqtt.qos.get("profile_upgrade_process") == 1


def test_qos_derive_profile_download():
    """TC-TOPIC-14: /profile/download → QoS profile_download=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/profile/download")
        assert qos == 1
        assert cfg.mqtt.qos.get("profile_download") == 1


def test_qos_derive_profile_download_process():
    """TC-TOPIC-15: /profile/download/process → QoS profile_download_process=1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/system/pk/dk/profile/download/process")
        assert qos == 1
        assert cfg.mqtt.qos.get("profile_download_process") == 1


def test_qos_default_is_one():
    """TC-TOPIC-16: Unknown topic defaults to QoS 1."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)
        qos = client._derive_qos_for_topic("/some/unknown/topic")
        assert qos == 1


def test_subscribe_topics_subscribes_all_10():
    """TC-TOPIC-17: _subscribe_topics subscribes exactly 10 topics (no reply_topic_pattern)."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient()
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        client._subscribe_topics()

    assert len(fake.subscriptions) == 10, f"Expected 10 subscriptions, got {len(fake.subscriptions)}: {fake.subscriptions}"


def test_is_command_reply_topic():
    """TC-TOPIC-19: Topics ending with _reply are detected as command replies."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)

    assert client._is_command_reply_topic("/system/pk/dk/thing/service/Reboot_reply") is True
    assert client._is_command_reply_topic("/system/pk/dk/thing/service/GetVersion_reply") is True
    assert client._is_command_reply_topic("/system/pk/dk/thing/property/post") is False
    assert client._is_command_reply_topic("/system/pk/dk/ota/upgrade") is False
    assert client._is_command_reply_topic("/system/pk/dk/profile/download") is False


# =============================================================================
# Reply detection edge cases (TC-REPLY-01 to TC-REPLY-04)
# =============================================================================


def test_is_command_reply_topic_suffix_check():
    """TC-REPLY-01: _is_command_reply_topic requires exact '_reply' suffix."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)

    assert client._is_command_reply_topic("/some/reply_to_thing") is False
    assert client._is_command_reply_topic("/device/reply_count") is False
    assert client._is_command_reply_topic("/thing/reply") is False
    assert client._is_command_reply_topic("/system/pk/dk/thing/service/Reboot_reply") is True


def test_is_command_reply_topic_exact_reply_suffix():
    """TC-REPLY-02: Exact '_reply' suffix is required."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    with patch("src.mqtt.client.mqtt.Client", return_value=FakeMQTTClient()):
        client = MqttClient(cfg)

    assert client._is_command_reply_topic("/system/pk/dk/thing/service/Reboot_reply") is True
    assert client._is_command_reply_topic("/system/pk/dk/thing/service/Reboot_reply_extra") is False


# =============================================================================
# Publish method tests (TC-PUBLISH-01 to TC-PUBLISH-05)
# =============================================================================


def test_publish_success():
    """TC-PUBLISH-01: publish() succeeds when client is connected."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient(connected=True)
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        result = client.publish("test/topic", '{"key": "value"}', qos=1)
    assert result is True


def test_publish_not_connected():
    """TC-PUBLISH-02: publish() returns False when client is not connected."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient(connected=False)
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        result = client.publish("test/topic", '{"key": "value"}', qos=1)
    assert result is False


def test_publish_none_client():
    """TC-PUBLISH-03: publish() returns False when client is None."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient(connected=True)
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        client._client = None
        result = client.publish("test/topic", '{"key": "value"}', qos=1)
    assert result is False


# =============================================================================
# Dynamic subscription tests (TC-SUB-01 to TC-SUB-04)
# =============================================================================


def test_subscribe_topic_dynamic():
    """TC-SUB-01: subscribe_topic() adds topic to subscriptions list."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient()
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        result = client.subscribe_topic("/system/pk/dk/thing/service/Reboot_reply", qos=1)
    assert result is True
    assert ("/system/pk/dk/thing/service/Reboot_reply", 1) in fake.subscriptions


def test_unsubscribe_topic_dynamic():
    """TC-SUB-02: unsubscribe_topic() removes topic from subscriptions list."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient()
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        client.subscribe_topic("/system/pk/dk/thing/service/Reboot_reply", qos=1)
        result = client.unsubscribe_topic("/system/pk/dk/thing/service/Reboot_reply")
    assert result is True


def test_subscribe_topic_when_client_none():
    """TC-SUB-03: subscribe_topic() returns False when client is None."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient()
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        client._client = None
        result = client.subscribe_topic("/test/topic", qos=1)
    assert result is False


# =============================================================================
# _parse_broker tests (TC-PARSE-01 to TC-PARSE-05)
# =============================================================================


def test_parse_broker_tcp_scheme():
    """TC-PARSE-01: tcp://host:port format is parsed correctly."""
    from src.mqtt.client import MqttClient

    host, port = MqttClient._parse_broker("tcp://192.168.1.100:1884")
    assert host == "192.168.1.100"
    assert port == 1884


def test_parse_broker_mqtts_scheme():
    """TC-PARSE-02: mqtts://host:port format is parsed correctly."""
    from src.mqtt.client import MqttClient

    host, port = MqttClient._parse_broker("mqtts://broker.example.com:8883")
    assert host == "broker.example.com"
    assert port == 8883


def test_parse_broker_no_scheme():
    """TC-PARSE-03: host:port without scheme is parsed correctly."""
    from src.mqtt.client import MqttClient

    host, port = MqttClient._parse_broker("localhost:1883")
    assert host == "localhost"
    assert port == 1883


def test_parse_broker_no_port():
    """TC-PARSE-04: plain host defaults to port 1883."""
    from src.mqtt.client import MqttClient

    host, port = MqttClient._parse_broker("mqtt.example.com")
    assert host == "mqtt.example.com"
    assert port == 1883


def test_parse_broker_whitespace():
    """TC-PARSE-05: broker URL with whitespace is trimmed."""
    from src.mqtt.client import MqttClient

    host, port = MqttClient._parse_broker("  tcp://localhost:1883  ")
    assert host == "localhost"
    assert port == 1883


# =============================================================================
# _schedule_reply_processing tests (TC-SCHED-01 to TC-SCHED-04)
# =============================================================================


def test_schedule_reply_processing_normal():
    """TC-SCHED-01: Valid reply JSON is parsed and scheduled on main loop."""
    from src.mqtt.client import MqttClient
    from src.config import load_config
    from unittest.mock import MagicMock

    cfg = load_config()
    fake = FakeMQTTClient()
    mock_loop = MagicMock()

    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        client._loop = mock_loop

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            client._schedule_reply_processing(
                "/system/pk/dk/thing/service/Reboot_reply",
                b'{"id": "msg-123", "code": 0, "message": "success"}',
            )

        mock_run.assert_called_once()
        coro, loop = mock_run.call_args[0]
        assert loop is mock_loop


def test_schedule_reply_processing_missing_id():
    """TC-SCHED-02: Reply without 'id' field logs error and returns early."""
    from src.mqtt.client import MqttClient
    from src.config import load_config
    from unittest.mock import MagicMock

    cfg = load_config()
    fake = FakeMQTTClient()
    mock_loop = MagicMock()

    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        client._loop = mock_loop

        import asyncio
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            client._schedule_reply_processing(
                "/system/pk/dk/thing/service/Reboot_reply",
                b'{"code": 0, "message": "success"}',
            )

        mock_run.assert_not_called()


def test_schedule_reply_processing_invalid_json():
    """TC-SCHED-03: Invalid JSON payload logs error and returns early."""
    from src.mqtt.client import MqttClient
    from src.config import load_config
    from unittest.mock import MagicMock

    cfg = load_config()
    fake = FakeMQTTClient()
    mock_loop = MagicMock()

    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        client._loop = mock_loop

        import asyncio
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            client._schedule_reply_processing(
                "/system/pk/dk/thing/service/Reboot_reply",
                b"not valid json",
            )

        mock_run.assert_not_called()


def test_schedule_reply_processing_no_loop():
    """TC-SCHED-04: When _loop is None, reply processing is skipped."""
    from src.mqtt.client import MqttClient
    from src.config import load_config
    from unittest.mock import MagicMock

    cfg = load_config()
    fake = FakeMQTTClient()

    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        client._loop = None

        import asyncio
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            client._schedule_reply_processing(
                "/system/pk/dk/thing/service/Reboot_reply",
                b'{"id": "msg-123", "code": 0}',
            )

        mock_run.assert_not_called()


# =============================================================================
# is_connected property tests (TC-CONN-01 to TC-CONN-02)
# =============================================================================


def test_is_connected_true():
    """TC-CONN-01: is_connected returns True when client is connected."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient(connected=True)
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
    assert client.is_connected is True


def test_is_connected_false():
    """TC-CONN-02: is_connected returns False when client is not connected."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient(connected=False)
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
    assert client.is_connected is False


# =============================================================================
# stop() method tests (TC-STOP-01)
# =============================================================================


def test_stop_sets_running_false():
    """TC-STOP-01: stop() sets _running to False and disconnects."""
    from src.mqtt.client import MqttClient
    from src.config import load_config

    cfg = load_config()
    fake = FakeMQTTClient()
    with patch("src.mqtt.client.mqtt.Client", return_value=fake):
        client = MqttClient(cfg)
        assert client._running is False

        client.start()
        assert client._running is True

        client.stop()
        assert client._running is False