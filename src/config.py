"""Configuration loader for MQTT-InfluxDB bridge service."""

from dataclasses import dataclass, field
from typing import Optional
import os
import yaml


@dataclass
class MQTTConfig:
    broker: str = "tcp://localhost:1883"
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "iot-bridge-001"
    clean_session: bool = False
    keepalive: int = 60
    topics: list = field(default_factory=lambda: [
        "/system/+/+/thing/property/post",
        "/system/+/+/thing/service/+",
        "/system/+/+/ota/upgrade",
        "/system/+/+/ota/get/reply",
        "/system/+/+/ota/upgrade/process",
        "/system/+/+/profile/upgrade",
        "/system/+/+/profile/get/reply",
        "/system/+/+/profile/upgrade/process",
        "/system/+/+/profile/download",
        "/system/+/+/profile/download/process",
    ])
    qos: dict = field(default_factory=lambda: {
        "property": 1,
        "service": 1,
        "service_reply": 1,
        "ota_upgrade": 1,
        "ota_get_reply": 1,
        "ota_upgrade_process": 1,
        "profile_upgrade": 1,
        "profile_get_reply": 1,
        "profile_upgrade_process": 1,
        "profile_download": 1,
        "profile_download_process": 1,
    })
    reply_topic_pattern: str = ""


@dataclass
class InfluxDBConfig:
    url: str = "http://localhost:8086"
    token: Optional[str] = None
    org: str = "my-org"
    database: str = "iot_data"


@dataclass
class HTTPConfig:
    host: str = "0.0.0.0"
    port: int = 6601


@dataclass
class BatchConfig:
    size: int = 5000
    flush_interval: int = 10  # seconds
    timeout: int = 30  # seconds


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "json"


@dataclass
class OpenClawConfig:
    webhook_secret: str = ""
    default_session_key: str = "agent:main:main"
    ws_url: str = "ws://localhost:18789"
    command_timeout_seconds: int = 30


@dataclass
class Config:
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    influxdb: InfluxDBConfig = field(default_factory=InfluxDBConfig)
    http: HTTPConfig = field(default_factory=HTTPConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    openclaw: OpenClawConfig = field(default_factory=OpenClawConfig)


def load_config(path: Optional[str] = None) -> Config:
    """Load config from YAML file with environment variable overrides."""
    if path is None:
        path = os.environ.get("CONFIG_PATH", "config.yaml")

    cfg = Config()

    # Try to load from file
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data:
            # Merge file config into dataclass
            if "mqtt" in data:
                cfg.mqtt = MQTTConfig(**{k.replace("-", "_"): v for k, v in data["mqtt"].items()})
            if "influxdb" in data:
                cfg.influxdb = InfluxDBConfig(**data["influxdb"])
            if "http" in data:
                cfg.http = HTTPConfig(**data["http"])
            if "batch" in data:
                cfg.batch = BatchConfig(**data["batch"])
            if "logging" in data:
                cfg.logging = LoggingConfig(**data["logging"])
            if "openclaw" in data:
                cfg.openclaw = OpenClawConfig(**data["openclaw"])

    # Environment variable overrides
    env_overrides = {
        "MQTT_BROKER": ("mqtt", "broker"),
        "INFLUXDB_URL": ("influxdb", "url"),
        "INFLUXDB_TOKEN": ("influxdb", "token"),
        "INFLUXDB_ORG": ("influxdb", "org"),
        "INFLUXDB_DATABASE": ("influxdb", "database"),
        "HTTP_HOST": ("http", "host"),
        "HTTP_PORT": ("http", "port"),
        "BATCH_SIZE": ("batch", "size"),
        "BATCH_FLUSH_INTERVAL": ("batch", "flush_interval"),
        "LOG_LEVEL": ("logging", "level"),
        "OPENCLAW_IOT_WEBHOOK_SECRET": ("openclaw", "webhook_secret"),
        "OPENCLAW_DEFAULT_SESSION_KEY": ("openclaw", "default_session_key"),
        "OPENCLAW_WS_URL": ("openclaw", "ws_url"),
    }

    for env_key, (section, field_name) in env_overrides.items():
        if env_key in os.environ:
            section_obj = getattr(cfg, section)
            current_value = getattr(section_obj, field_name)
            raw_value = os.environ[env_key]

            # Keep env overrides type-safe, especially for int/bool fields.
            if isinstance(current_value, bool):
                value = raw_value.strip().lower() in {"1", "true", "yes", "on"}
            elif isinstance(current_value, int):
                value = int(raw_value)
            elif isinstance(current_value, float):
                value = float(raw_value)
            else:
                value = raw_value

            setattr(section_obj, field_name, value)

    return cfg