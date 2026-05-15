"""WebSocket client for OpenClaw Gateway sessions.send API."""

import asyncio
import json
import logging
from typing import Optional

import websockets.asyncio.client
from websockets import ConnectionClosed

logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket client that pushes command results to OpenClaw Gateway via sessions.send.

    Manages a persistent connection with auto-reconnect (exponential backoff).
    Uses websockets library's built-in async-for reconnect pattern.
    """

    def __init__(
        self,
        ws_url: str,
        token: str,
        default_session_key: str,
    ):
        self.ws_url = ws_url
        self.token = token
        self.default_session_key = default_session_key
        self._ws: Optional[websockets.asyncio.client.ClientConnection] = None
        self._pending_queue: list[dict] = []
        self._connected = False

    def send_command_result(
        self,
        session_key: str,
        message_id: str,
        device_key: str,
        service_name: str,
        status: str,
        reply: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> bool:
        """Construct and queue/send a command result notification via sessions.send.

        Args:
            session_key: Target Agent session key.
            message_id: Command message ID.
            device_key: Device identifier.
            service_name: Command service name.
            status: "completed" or "timeout".
            reply: Optional MQTT reply payload.
            params: Optional command parameters.

        Returns:
            True if the message was sent or queued successfully.
        """
        message_data: dict[str, object] = {
            "type": "command_result",
            "message_id": message_id,
            "device_key": device_key,
            "service_name": service_name,
            "status": status,
        }
        if reply is not None:
            message_data["reply"] = reply
        if params is not None:
            message_data["params"] = params

        payload = {
            "method": "sessions.send",
            "params": {
                "key": session_key,
                "message": json.dumps(message_data, ensure_ascii=False),
            },
        }

        if self._connected and self._ws is not None:
            try:
                asyncio.create_task(self._do_send(payload))
            except Exception as e:
                logger.warning(f"Failed to send WS message: {e}, queuing instead")
                self._pending_queue.append(payload)
        else:
            self._pending_queue.append(payload)
            logger.debug(f"WS not connected, queued message for {message_id}")

        return True

    async def _do_handshake(self, ws) -> bool:
        """Perform Gateway challenge-response handshake.

        OpenClaw Gateway requires a two-step authentication after WebSocket connect:
        1. Server sends 'connect.challenge' event with a nonce
        2. Client responds with 'connect' request (type=req, method=connect)
           containing auth token, valid client ID, and protocol version
        3. Server responds with 'res' with ok=true on success

        Protocol details from Gateway source (protocol/schema/frames.ts):
        - Request format: {type: "req", id: "...", method: "connect", params: {...}}
        - params.client.id must be from GATEWAY_CLIENT_IDS enum
        - params.minProtocol/maxProtocol must match server (currently 3)
        - nonce is NOT a separate field; it's only within device auth object

        Returns True if handshake succeeded, False otherwise.
        """
        try:
            # Step 1: Read the challenge event
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            challenge = json.loads(raw)
            if challenge.get("event") != "connect.challenge":
                logger.error(f"Expected connect.challenge, got: {challenge.get('event')}")
                return False

            nonce = challenge.get("payload", {}).get("nonce", "")
            if not nonce:
                logger.error("connect.challenge missing nonce")
                return False

            logger.debug(f"Gateway challenge received, nonce={nonce[:8]}...")

            # Step 2: Send connect request in correct Gateway frame format
            # Must match ConnectParamsSchema: type=req, method=connect, protocol=3
            connect_msg: dict = {
                "type": "req",
                "id": f"connect-{nonce[:8]}",
                "method": "connect",
                "params": {
                    "minProtocol": 3,
                    "maxProtocol": 3,
                    "client": {
                        "id": "gateway-client",
                        "version": "1.0.0",
                        "platform": "python",
                        "mode": "backend",
                    },
                    "auth": {"token": self.token},
                    "role": "operator",
                },
            }
            await ws.send(json.dumps(connect_msg))

            # Step 3: Wait for connect response
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            resp = json.loads(raw)
            if resp.get("type") == "res" and resp.get("ok"):
                logger.info("Gateway handshake successful")
                return True
            else:
                error_msg = resp.get("error", {}).get("message", str(resp))
                logger.error(f"Gateway handshake failed: {error_msg}")
                return False

        except asyncio.TimeoutError:
            logger.error("Gateway handshake timed out")
            return False
        except Exception as e:
            logger.error(f"Gateway handshake error: {e}")
            return False

    async def connect(self):
        """Connect to Gateway WebSocket and maintain connection with auto-reconnect.

        Performs challenge-response handshake on each connection.
        Uses websockets async-for iterator pattern for automatic reconnection
        with exponential backoff. On reconnect, flushes the pending queue.
        """
        headers = {"Authorization": f"Bearer {self.token}"}

        async for ws in websockets.asyncio.client.connect(
            self.ws_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=20,
        ):
            # Perform authentication handshake
            if not await self._do_handshake(ws):
                logger.warning("Gateway handshake failed, will reconnect...")
                await ws.close(1008, "handshake failed")
                continue

            self._ws = ws
            self._connected = True
            logger.info(f"WebSocket connected to {self.ws_url}")

            # Flush pending queue on (re)connect
            await self._flush_pending_queue(ws)

            try:
                # Keep connection alive, consume inbound messages
                async for msg in ws:
                    # Log unexpected messages at debug level
                    logger.debug(f"WS received: {msg[:100]}")
            except ConnectionClosed:
                logger.info("WebSocket connection closed, will reconnect...")
            finally:
                self._connected = False
                self._ws = None

    async def _flush_pending_queue(self, ws):
        """Send all queued messages on (re)connect."""
        if not self._pending_queue:
            return
        logger.info(f"Flushing {len(self._pending_queue)} queued WS messages")
        for payload in self._pending_queue:
            try:
                await ws.send(json.dumps(payload))
            except Exception as e:
                logger.warning(f"Failed to flush queued message: {e}")
        self._pending_queue.clear()

    async def _do_send(self, payload: dict):
        """Send a single payload over the current WebSocket connection."""
        if self._ws is None or not self._connected:
            logger.warning("Cannot send: WebSocket not connected")
            return
        try:
            await self._ws.send(json.dumps(payload))
            # Don't wait for ack here to avoid blocking the caller
            logger.debug(f"Sent WS message: method={payload.get('method')}")
        except ConnectionClosed:
            logger.warning("WS connection closed during send, message lost")
            self._connected = False
            self._ws = None
        except Exception as e:
            logger.warning(f"WS send failed: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self._connected
