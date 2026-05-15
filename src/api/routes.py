"""FastAPI route definitions for the IoT bridge service."""
import asyncio
import json
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.api.models import HealthResponse, SQLQueryRequest, SQLQueryResponse, ErrorResponse
from src.config import Config
from src.mqtt.client import MqttClient
from src.influxdb.writer import InfluxDBWriter
from src.influxdb.query import InfluxDBQuery
from src.models.command import CommandRequest, CommandResponse, build_service_topic, build_command_payload
from src.ws_client import WebSocketClient
import uuid

logger = logging.getLogger(__name__)

# App-level globals (set by main.py on startup)
config: Config = None
mqtt_client: MqttClient = None
influxdb_writer: InfluxDBWriter = None
influxdb_query: InfluxDBQuery = None
ws_client: WebSocketClient = None
start_time: float = time.time()

# Command state storage: message_id → command state dict
_commands_map: dict[str, dict] = {}
# Timeout task tracking: message_id → asyncio.Task
_timeout_task_map: dict[str, asyncio.Task] = {}


def _persist_commands():
    """Persist command state to disk (async-safe, best-effort)."""
    try:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        path = os.path.join(data_dir, "commands.json")
        with open(path, "w") as f:
            json.dump(_commands_map, f, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning(f"Failed to persist commands: {e}")


async def _schedule_timeout(message_id: str, timeout_seconds: int = 30):
    """Wait for timeout, then mark command as timed out if still pending."""
    try:
        await asyncio.sleep(timeout_seconds)
        cmd = _commands_map.get(message_id)
        if cmd and cmd["status"] == "pending":
            cmd["status"] = "timeout"
            _persist_commands()
            logger.info(f"Command {message_id} timed out after {timeout_seconds}s")
            if ws_client:
                ws_client.send_command_result(
                    session_key=cmd["session_key"],
                    message_id=message_id,
                    device_key=cmd["device_key"],
                    service_name=cmd["service_name"],
                    status="timeout",
                )
    except asyncio.CancelledError:
        logger.debug(f"Timeout cancelled for {message_id}")
    except Exception as e:
        logger.error(f"Timeout check failed for {message_id}: {e}")
    finally:
        _timeout_task_map.pop(message_id, None)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=time.time() - start_time,
        mqtt_connected=mqtt_client.is_connected if mqtt_client else False,
        influxdb_connected=influxdb_writer.is_connected if influxdb_writer else False,
    )


@router.get("/api/v1/devices")
async def list_devices():
    """List all known devices."""
    if not influxdb_query:
        raise HTTPException(status_code=503, detail="InfluxDB not available")
    try:
        devices = influxdb_query.get_devices()
        return {"success": True, "data": devices, "count": len(devices)}
    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail=f"Query failed: {str(e)}").model_dump(),
        )


@router.get("/api/v1/devices/{device_id}")
async def get_device(device_id: str):
    """Get device details and latest telemetry."""
    if not influxdb_query:
        raise HTTPException(status_code=503, detail="InfluxDB not available")
    try:
        result = influxdb_query.get_device_telemetry(device_id, limit=1)
        if result["success"] and result["data"]:
            latest = result["data"][0]
            return {"success": True, "device_id": device_id, "latest": latest}
        return {"success": True, "device_id": device_id, "latest": None}
    except Exception as e:
        logger.error(f"Failed to get device {device_id}: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail=str(e)).model_dump(),
        )


@router.get("/api/v1/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str,
    start: str = Query(default="-1h", description="Start time"),
    end: str = Query(default="now", description="End time"),
    limit: int = Query(default=100, ge=1, le=10000, description="Max results"),
):
    """Get telemetry history for a device."""
    if not influxdb_query:
        raise HTTPException(status_code=503, detail="InfluxDB not available")
    try:
        result = influxdb_query.get_device_telemetry(device_id, start, end, limit)
        return {
            "success": result["success"],
            "device_id": device_id,
            "data": result.get("data", []),
            "meta": result.get("meta"),
            "error": result.get("error"),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail=str(e)).model_dump(),
        )


@router.get("/api/v1/devices/{device_id}/status")
async def get_device_status(device_id: str):
    """Get latest device status.

    Returns the most recent telemetry record for the device,
    using a 30-day window to match get_devices() visibility.
    """
    # In a production system, status would come from a separate measurement
    # For now, it's the latest telemetry record
    return await get_device_telemetry(device_id, start="-30d", end="now", limit=1)


@router.post("/api/v1/query", response_model=SQLQueryResponse)
async def post_query(req: SQLQueryRequest):
    """Execute a raw SQL query against InfluxDB."""
    if not influxdb_query:
        return SQLQueryResponse(
            success=False,
            error="InfluxDB not available (mock mode)",
        )
    try:
        result = influxdb_query.query_sql(req.sql, database=req.database)
        return SQLQueryResponse(
            success=result["success"],
            data=result.get("data", []),
            meta=result.get("meta"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Query error: {e}")
        return SQLQueryResponse(success=False, error=str(e))


@router.post("/api/v1/commands", response_model=CommandResponse)
async def send_command(req: CommandRequest):
    """Send a command to a device via MQTT."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not available")

    message_id = req.id or str(uuid.uuid4())
    topic = build_service_topic(req.product_key, req.device_key, req.service_name)
    payload = build_command_payload(req.service_name, req.params, message_id)
    session_key = req.session_key or config.openclaw.default_session_key

    # Subscribe to reply topic before publishing command
    reply_topic = f"/system/{req.product_key}/{req.device_key}/thing/service/{req.service_name}_reply"
    mqtt_client.subscribe_topic(reply_topic, qos=1)

    logger.info(f"Sending command to {req.device_key}/{req.service_name}, message_id={message_id}")

    # Publish MQTT command
    success = mqtt_client.publish(topic, payload)
    if not success:
        return JSONResponse(
            status_code=500,
            content=CommandResponse(
                success=False, message_id=message_id,
                topic=topic, payload=payload,
                detail="MQTT publish failed",
            ).model_dump(),
        )

    # Store command state locally
    _commands_map[message_id] = {
        "status": "pending",
        "product_key": req.product_key,
        "device_key": req.device_key,
        "service_name": req.service_name,
        "params": req.params,
        "session_key": session_key,
        "topic": topic,
        "created_at": time.time(),
        "reply_data": None,
    }
    _persist_commands()

    # Start timeout check
    _timeout_task_map[message_id] = asyncio.create_task(
        _schedule_timeout(message_id, timeout_seconds=config.openclaw.command_timeout_seconds)
    )

    return CommandResponse(
        success=True,
        message_id=message_id,
        topic=topic,
        payload=payload,
        session_key=session_key,
    )


@router.get("/api/v1/commands/{message_id}/status")
async def get_command_status(message_id: str):
    """Get command execution status from local state."""
    try:
        cmd = _commands_map.get(message_id)
        if not cmd:
            return {
                "success": False,
                "message_id": message_id,
                "error": f"No command found for message_id={message_id}",
            }
        return {
            "success": True,
            "message_id": message_id,
            "status": cmd.get("status", "unknown"),
            "state": cmd.get("reply_data"),
        }
    except Exception as e:
        logger.warning(f"Failed to get command status for {message_id}: {e}")
        return {
            "success": False,
            "message_id": message_id,
            "error": str(e),
        }


async def on_command_reply(message_id: str, reply_data: dict):
    """Handle MQTT command reply - update local state and push via WS."""
    try:
        cmd = _commands_map.get(message_id)
        if not cmd:
            logger.error(f"Command reply: no command found for message_id={message_id}")
            return

        # Update local state
        cmd["status"] = "completed"
        cmd["reply_data"] = reply_data
        _persist_commands()

        # Cancel timeout task if still running
        timeout_task = _timeout_task_map.pop(message_id, None)
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()

        # Push notification via WebSocket
        if ws_client:
            ws_client.send_command_result(
                session_key=cmd["session_key"],
                message_id=message_id,
                device_key=cmd["device_key"],
                service_name=cmd["service_name"],
                status="completed",
                reply=reply_data,
                params=cmd.get("params"),
            )

        logger.info(f"Completed command {message_id}")
    except Exception as e:
        logger.error(f"Failed to complete command {message_id}: {e}")


def handle_command_reply(client, userdata, msg):
    """MQTT callback for command replies - delegates to async handler."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        message_id = payload.get("id", "")
        if not message_id:
            logger.error(f"Command reply missing 'id' field, topic={msg.topic}")
            return
        logger.info(f"Command reply received: message_id={message_id}, topic={msg.topic}")
        asyncio.create_task(on_command_reply(message_id, payload))
    except json.JSONDecodeError as e:
        logger.error(f"Command reply JSON parse error, topic={msg.topic}: {e}")
    except Exception as e:
        logger.error(f"Command reply handler error, topic={msg.topic}: {e}")


