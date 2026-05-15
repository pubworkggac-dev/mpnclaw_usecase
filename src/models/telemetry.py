"""Data models for telemetry messages from IoT devices."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, timezone


class TelemetryMessage(BaseModel):
    """A single telemetry data point from an IoT device."""
    device_id: str = Field(..., description="Unique device identifier")
    sensor_type: str = Field(default="unknown", description="Type of sensor")
    location: Optional[str] = Field(default=None, description="Device location")
    value: float = Field(..., description="Measured value (float)")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")
    timestamp: Optional[int] = Field(default=None, description="Unix millisecond timestamp. If None, use server time.")

    model_config = ConfigDict(extra="ignore")


class DeviceStatus(BaseModel):
    """Device online/offline/alert status."""
    device_id: str
    status: str = Field(default="online", pattern="^(online|offline|alert)$")
    timestamp: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))
    message: Optional[str] = None


class DeviceInfo(BaseModel):
    """Device summary info returned by API."""
    device_id: str
    last_seen: Optional[int] = None
    last_value: Optional[float] = None
    sensor_type: Optional[str] = None
    location: Optional[str] = None


class DeviceEvent(BaseModel):
    """Device event (e.g., button press, motion detected)."""
    device_id: str
    event_type: str
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[int] = None