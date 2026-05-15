"""API request/response models."""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    uptime_seconds: Optional[float] = None
    mqtt_connected: bool = False
    influxdb_connected: bool = False


class SQLQueryRequest(BaseModel):
    sql: str = Field(..., description="SQL query string")
    database: Optional[str] = None


class SQLQueryResponse(BaseModel):
    success: bool = True
    data: list = Field(default_factory=list, description="Query result rows")
    meta: Optional[dict] = Field(default=None, description="Column metadata")
    error: Optional[str] = None


class TelemetryQueryParams(BaseModel):
    device_id: str
    start: Optional[str] = Field(default="-1h", description="Start time (RFC3339 or relative)")
    end: Optional[str] = Field(default="now", description="End time (RFC3339 or now)")
    limit: int = Field(default=100, ge=1, le=10000, description="Max results")


class StatusQueryParams(BaseModel):
    device_id: str
    limit: int = Field(default=1, ge=1, le=100)


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None