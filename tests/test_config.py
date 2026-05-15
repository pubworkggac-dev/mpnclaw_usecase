"""Tests for config module."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set config path before importing config module
os.environ["CONFIG_PATH"] = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

def test_default_config():
    """Test that config loads with defaults from config.yaml."""
    from src.config import load_config
    cfg = load_config()
    assert cfg.mqtt.broker == "tcp://localhost:1883"
    assert cfg.influxdb.database == "iot_data"
    assert cfg.http.port == 6601
    assert cfg.batch.size == 5000
    assert cfg.batch.flush_interval == 10

def test_env_override(monkeypatch):
    """Test environment variable overrides config file."""
    monkeypatch.setenv("MQTT_BROKER", "tcp://test-broker:1883")
    from src.config import load_config
    cfg = load_config()
    assert cfg.mqtt.broker == "tcp://test-broker:1883"


def test_jiujingyun_topics_loaded():
    """TC-TOPIC-01: Verify all 10 Jiujingyun topics are loaded (note: +_reply removed - invalid MQTT wildcard)."""
    from src.config import load_config
    cfg = load_config()
    topics = cfg.mqtt.topics
    assert len(topics) == 10, f"Expected 10 topics, got {len(topics)}: {topics}"
    # property post
    assert "/system/+/+/thing/property/post" in topics
    # service + (reply topics are dynamically subscribed before sending commands)
    assert "/system/+/+/thing/service/+" in topics
    # ota
    assert "/system/+/+/ota/upgrade" in topics
    assert "/system/+/+/ota/get/reply" in topics
    assert "/system/+/+/ota/upgrade/process" in topics
    # profile
    assert "/system/+/+/profile/upgrade" in topics
    assert "/system/+/+/profile/get/reply" in topics
    assert "/system/+/+/profile/upgrade/process" in topics
    assert "/system/+/+/profile/download" in topics
    assert "/system/+/+/profile/download/process" in topics


def test_legacy_topics_removed():
    """TC-TOPIC-02: Verify non-Jiujingyun topics are removed."""
    from src.config import load_config
    cfg = load_config()
    topics = cfg.mqtt.topics
    assert "devices/+/telemetry" not in topics
    assert "devices/+/status" not in topics


def test_reply_topic_pattern_empty():
    """TC-TOPIC-03: Verify reply_topic_pattern is empty (replied topics now in topics list)."""
    from src.config import load_config
    cfg = load_config()
    assert cfg.mqtt.reply_topic_pattern == ""


def test_qos_keys_complete():
    """TC-TOPIC-04: Verify qos dict contains all 11 keys for Jiujingyun topics."""
    from src.config import load_config
    cfg = load_config()
    expected_keys = {
        "property", "service", "service_reply",
        "ota_upgrade", "ota_get_reply", "ota_upgrade_process",
        "profile_upgrade", "profile_get_reply", "profile_upgrade_process",
        "profile_download", "profile_download_process",
    }
    actual_keys = set(cfg.mqtt.qos.keys())
    missing = expected_keys - actual_keys
    assert not missing, f"Missing QoS keys: {missing}"