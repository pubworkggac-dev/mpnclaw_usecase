"""MQTT-InfluxDB Bridge Service - Entry Point.

A service that subscribes to MQTT topics, batches telemetry messages,
and writes them to InfluxDB v2. Provides HTTP API for querying data.
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.config import load_config
from src.mqtt.client import MqttClient
from src.influxdb.writer import InfluxDBWriter
from src.influxdb.query import InfluxDBQuery
from src.ws_client import WebSocketClient
from src.api import routes

logger = logging.getLogger("mqtt-influxdb-bridge")


def setup_logging(level: str, log_format: str):
    """Configure structured logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    if log_format == "json":
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}'
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=log_level,
        format=fmt,
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        stream=sys.stdout,
    )


def main():
    """Application entry point."""
    cfg = load_config()
    setup_logging(cfg.logging.level, cfg.logging.format)
    logger.info(f"Starting MQTT-InfluxDB Bridge v1.0.0")
    logger.info(f"MQTT broker: {cfg.mqtt.broker}")
    logger.info(f"InfluxDB: {cfg.influxdb.url}/{cfg.influxdb.database}")

    # Initialize components
    query = InfluxDBQuery(cfg)
    query.connect()

    writer = InfluxDBWriter(cfg)
    writer.start()

    # Wire MQTT messages -> InfluxDB writer
    mqtt = MqttClient(
        cfg,
        on_message_callback=writer.write,
    )
    mqtt.start()

    # Expose components to routes module
    routes.config = cfg
    routes.mqtt_client = mqtt
    routes.influxdb_writer = writer
    routes.influxdb_query = query

    # Initialize WebSocket client to Gateway
    ws_client = WebSocketClient(
        ws_url=cfg.openclaw.ws_url,
        token=cfg.openclaw.webhook_secret,
        default_session_key=cfg.openclaw.default_session_key,
    )
    routes.ws_client = ws_client

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Capture the running event loop and start WS client."""
        mqtt.set_main_loop(asyncio.get_running_loop())
        # Start WebSocket client as background task
        ws_task = asyncio.create_task(ws_client.connect())
        logger.info(f"WebSocket client started: {cfg.openclaw.ws_url}")
        yield
        # Cleanup on shutdown
        ws_task.cancel()
        logger.info("WebSocket client stopped")

    # Build FastAPI app and mount routes.
    app = FastAPI(title="mqtt-influxdb-bridge", version="1.0.0", lifespan=lifespan)
    app.include_router(routes.router)

    # Start HTTP server
    logger.info(f"HTTP API: http://{cfg.http.host}:{cfg.http.port}")
    uvicorn.run(
        app,
        host=cfg.http.host,
        port=cfg.http.port,
        log_level=cfg.logging.level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()