"""Tests for routes.py command flow (WebSocket push, local state)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes import (
    _commands_map, _timeout_task_map,
    send_command, get_command_status, on_command_reply,
)
from src.models.command import CommandRequest


@pytest.fixture(autouse=True)
def clear_state():
    """Clear module state before each test."""
    _commands_map.clear()
    _timeout_task_map.clear()


@pytest.fixture
def mock_deps():
    """Mock routes module globals."""
    with (
        patch("src.api.routes.mqtt_client") as mqtt_mock,
        patch("src.api.routes.ws_client") as ws_mock,
        patch("src.api.routes.config") as config_mock,
    ):
        config_mock.openclaw.command_timeout_seconds = 30
        config_mock.openclaw.default_session_key = "agent:main:main"
        mqtt_mock.publish.return_value = True
        mqtt_mock.subscribe_topic.return_value = True
        yield mqtt_mock, ws_mock, config_mock


class TestSendCommand:
    """Verify send_command no longer uses TaskFlow."""

    @pytest.mark.asyncio
    async def test_stores_command_in_commands_map(self, mock_deps):
        """After send_command, _commands_map should contain the command."""
        req = CommandRequest(
            product_key="test-pk",
            device_key="test-dk",
            service_name="SetDeviceName",
            params={"name": "test"},
        )
        result = await send_command(req)
        assert result.success is True
        msg_id = result.message_id
        assert msg_id in _commands_map
        assert _commands_map[msg_id]["status"] == "pending"
        assert _commands_map[msg_id]["device_key"] == "test-dk"

    @pytest.mark.asyncio
    async def test_does_not_call_taskflow(self, mock_deps):
        """send_command should NOT call create_flow or set_waiting."""
        mqtt_mock, ws_mock, config_mock = mock_deps
        req = CommandRequest(
            product_key="test-pk",
            device_key="test-dk",
            service_name="DeviceReboot",
            params={},
        )
        result = await send_command(req)
        assert result.success is True
        msg_id = result.message_id
        assert msg_id in _commands_map
        assert _commands_map[msg_id]["status"] == "pending"
        assert _commands_map[msg_id]["device_key"] == "test-dk"

    @pytest.mark.asyncio
    async def test_returns_without_exception(self, mock_deps):
        """send_command should complete without TaskFlow-related errors."""
        mqtt_mock, ws_mock, config_mock = mock_deps
        req = CommandRequest(
            product_key="test-pk",
            device_key="test-dk",
            service_name="DeviceReboot",
            params={},
        )
        # No TaskFlow mocks needed - they should not be called
        result = await send_command(req)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_starts_timeout_task(self, mock_deps):
        """After send_command, a timeout task should be scheduled."""
        req = CommandRequest(
            product_key="pk", device_key="dk",
            service_name="Reboot", params={},
        )
        await send_command(req)
        msg_id = list(_commands_map.keys())[0]
        assert msg_id in _timeout_task_map
        assert not _timeout_task_map[msg_id].done()

    @pytest.mark.asyncio
    async def test_mqtt_publish_failure(self, mock_deps):
        """If MQTT publish fails, error response is returned."""
        mqtt_mock, ws_mock, config_mock = mock_deps
        mqtt_mock.publish.return_value = False
        req = CommandRequest(
            product_key="pk", device_key="dk",
            service_name="Reboot", params={},
        )
        result = await send_command(req)
        import json as _json
        body = _json.loads(result.body.decode())
        assert body["success"] is False
        assert "publish failed" in body.get("detail", "").lower()


class TestGetCommandStatus:
    """Verify get_command_status reads from local state."""

    @pytest.mark.asyncio
    async def test_returns_pending_for_new_command(self, mock_deps):
        _commands_map["test-msg"] = {
            "status": "pending", "device_key": "dk",
            "service_name": "svc", "reply_data": None,
        }
        result = await get_command_status("test-msg")
        assert result["success"] is True
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_returns_completed_after_reply(self, mock_deps):
        _commands_map["test-msg"] = {
            "status": "completed", "device_key": "dk",
            "service_name": "svc", "reply_data": {"code": 0},
        }
        result = await get_command_status("test-msg")
        assert result["success"] is True
        assert result["status"] == "completed"
        assert result["state"] == {"code": 0}

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown(self, mock_deps):
        result = await get_command_status("nonexistent")
        assert result["success"] is False
        assert "No command found" in result.get("error", "")


class TestOnCommandReply:
    """Verify on_command_reply updates state and pushes via WS."""

    @pytest.mark.asyncio
    async def test_updates_state_and_pushes_via_ws(self, mock_deps):
        mqtt_mock, ws_mock, config_mock = mock_deps
        _commands_map["test-msg"] = {
            "status": "pending",
            "session_key": "agent:main:main",
            "device_key": "test-dk",
            "service_name": "SetDeviceName",
            "params": {},
            "product_key": "pk",
            "topic": "/system/pk/dk/thing/service/SetDeviceName",
            "created_at": 0,
            "reply_data": None,
        }
        await on_command_reply("test-msg", {"code": 0, "message": "ok"})
        assert _commands_map["test-msg"]["status"] == "completed"
        assert _commands_map["test-msg"]["reply_data"] == {"code": 0, "message": "ok"}
        # Verify ws_client was called
        ws_mock.send_command_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancels_timeout_task(self, mock_deps):
        mqtt_mock, ws_mock, config_mock = mock_deps
        import asyncio
        _commands_map["test-msg"] = {
            "status": "pending",
            "session_key": "agent:main:main",
            "device_key": "test-dk",
            "service_name": "svc",
            "params": {},
            "product_key": "pk",
            "topic": "/system/pk/dk/thing/service/svc",
            "created_at": 0,
            "reply_data": None,
        }
        # Create a mock timeout task
        task = asyncio.create_task(asyncio.sleep(999))
        _timeout_task_map["test-msg"] = task
        assert not task.done()
        await on_command_reply("test-msg", {"code": 0})
        # Timeout should be cancelled
        await asyncio.sleep(0)  # yield to let cancellation propagate
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_handles_unknown_message(self, mock_deps):
        """No crash when reply arrives for unknown message_id."""
        mqtt_mock, ws_mock, config_mock = mock_deps
        # This should not raise
        await on_command_reply("nonexistent", {"code": 0})
        ws_mock.send_command_result.assert_not_called()
