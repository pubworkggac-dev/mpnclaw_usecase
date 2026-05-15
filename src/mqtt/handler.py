import json
import logging
from typing import Callable

from src.models.telemetry import TelemetryMessage
from src.adapters import SimpleAdapter, JiujingyunAdapter, FormatRouter

logger = logging.getLogger(__name__)

MessageCallback = Callable[[TelemetryMessage], None]

_router: FormatRouter | None = None


def _get_router() -> FormatRouter:
    global _router
    if _router is None:
        _router = FormatRouter()
        _router.register(JiujingyunAdapter())
        _router.register(SimpleAdapter())
    return _router


def create_message_handler(callback: MessageCallback):
    router = _get_router()

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)

            telemetry = router.parse(msg.topic, data)

            if telemetry:
                logger.debug(f"Parsed telemetry: device={telemetry.device_id}, value={telemetry.value}")
                callback(telemetry)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error on topic {msg.topic}: {e}")
        except Exception as e:
            logger.error(f"Message handler error: {e}", exc_info=True)

    return on_message