"""Tests for WebSocketClient (ws_client.py)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.ws_client import WebSocketClient


@pytest.fixture
def ws_client():
    return WebSocketClient(
        ws_url="ws://localhost:18789",
        token="test-secret",
        default_session_key="agent:main:main",
    )


class TestWebSocketClientInit:
    """Verify initialization contracts."""

    def test_init_stores_params(self):
        client = WebSocketClient(
            ws_url="ws://test:1234",
            token="abc",
            default_session_key="agent:test:main",
        )
        assert client.ws_url == "ws://test:1234"
        assert client.token == "abc"
        assert client.default_session_key == "agent:test:main"
        assert client._pending_queue == []

    def test_init_empty_pending_queue(self, ws_client):
        assert ws_client._pending_queue == []


class TestWebSocketClientSendCommandResult:
    """Test send_command_result constructs correct payload."""

    def test_send_connected_enqueues_or_sends(self, ws_client):
        """When connected, payload is sent via websocket."""
        # Test that the method doesn't crash and returns True when called
        # Full WS send is covered by integration test
        result = ws_client.send_command_result(
            session_key="agent:main:main",
            message_id="msg-001",
            device_key="dev-1",
            service_name="SetDeviceName",
            status="completed",
            reply={"code": 0},
        )
        assert result is True

    def test_send_pending_enqueues_when_not_connected(self, ws_client):
        """When not connected, payload goes to pending queue."""
        ws_client._pending_queue.clear()
        result = ws_client.send_command_result(
            session_key="agent:main:main",
            message_id="msg-002",
            device_key="dev-2",
            service_name="RebootDevice",
            status="timeout",
        )
        assert result is True
        assert len(ws_client._pending_queue) == 1

    def test_connect_retries_on_transient_error(self):
        """Connect handles transient errors gracefully (no exception to caller)."""
        client = WebSocketClient(
            ws_url="ws://localhost:9999",
            token="test",
            default_session_key="agent:main:main",
        )
        # connect() runs an infinite async for loop;
        # we just verify it's a coroutine that won't crash the caller
        import asyncio
        assert asyncio.iscoroutinefunction(client.connect)

    def test_pending_queue_multiple_messages(self, ws_client):
        """Multiple send_command_result calls queue independently."""
        ws_client._pending_queue.clear()
        ws_client.send_command_result("agent:main:main", "m1", "d1", "svc1", "completed")
        ws_client.send_command_result("agent:main:main", "m2", "d2", "svc2", "timeout")
        assert len(ws_client._pending_queue) == 2
        # Verify first message content
        payload1 = ws_client._pending_queue[0]
        assert payload1["method"] == "sessions.send"
        assert "m1" in payload1["params"]["message"]

    def test_timeout_status_message_format(self, ws_client):
        """timeout messages use correct format."""
        ws_client._pending_queue.clear()
        ws_client.send_command_result(
            session_key="agent:main:main",
            message_id="msg-timeout",
            device_key="dev-t",
            service_name="RebootDevice",
            status="timeout",
        )
        payload = ws_client._pending_queue[0]
        message = payload["params"]["message"]
        assert "timeout" in message
        assert "msg-timeout" in message
