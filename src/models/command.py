"""Data models for device command messages (九井云 IoT protocol)."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
import uuid


class DeviceCommand(BaseModel):
    """Platform-to-device command following 九井云 MQTT service protocol.

    Topic: /system/{productKey}/{deviceKey}/thing/service/{serviceName}
    Payload format per 九井云 documentation.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="唯一id")
    version: str = Field(default="1.0.0", description="协议版本")
    params: Dict[str, Any] = Field(..., description="命令参数")
    method: str = Field(..., description="服务方法名，如 thing.service.SetDeviceName")

    model_config = ConfigDict(extra="ignore")


class CommandRequest(BaseModel):
    """Internal API model for sending commands via REST."""
    product_key: str = Field(..., description="产品唯一标识")
    device_key: str = Field(..., description="设备唯一标识")
    service_name: str = Field(..., description="服务名称，如 SetDeviceName")
    params: Dict[str, Any] = Field(..., description="命令参数")
    id: Optional[str] = Field(default=None, description="命令id，默认自动生成")
    session_key: Optional[str] = Field(
        default=None,
        description="OpenClaw 会话标识，未传时使用配置文件中的 default_session_key",
    )


class CommandResponse(BaseModel):
    """Response model for command submission."""
    success: bool
    message_id: str
    topic: str
    payload: str
    detail: Optional[str] = None
    session_key: Optional[str] = Field(
        default=None, description="命令绑定的 OpenClaw 会话标识"
    )


class DeviceCommandReply(BaseModel):
    """Device reply to command (from MQTT subscribe)."""
    code: int = Field(..., description="状态码，200表示成功")
    data: Dict[str, Any] = Field(default_factory=dict, description="执行结果数据")
    id: str = Field(..., description="对应平台下发内容的id")
    message: str = Field(default="success", description="消息")
    version: str = Field(default="1.0", description="协议版本")

    model_config = ConfigDict(extra="ignore")


# 九井云 服务列表 (用于验证service_name)
JIUJINGYUN_SERVICES = [
    "SetDeviceName", "SetNTPConfig", "SetUserInfo", "SetCMNDeviceCloudConfig",
    "SetCMNJiuJingCloudConfig", "SetCMNTR069Config", "DeviceReboot", "WANPPPOEConfig",
    "WANSTATICConfig", "WANDHCPConfig", "WANPriority", "LANConfig",
    "MobileNetworkConfig", "FiveGLANConfig", "LockScreenLockCommunity",
    "AgentSwitch", "SetPostRoute", "SIMConfig", "HotStandby", "VLANConfig",
    "IPToMac", "RouteConfig", "MoudleStayOnline", "VPDN", "IPSEC", "GRE",
    "VXLAN", "RS485", "RS232", "NATForwardingConfig", "DMZ",
    "RoutingBridgeConfig", "PasswordFreeLogin", "IpMacFilter", "DomainFilter",
    "SetCmdFun", "TraceRoute", "SetDNS", "RestoreFactorySettings",
    "AppUninstall", "AppInstall", "SyncPCTime", "RebootDevice", "SetPING",
]


def build_service_topic(product_key: str, device_key: str, service_name: str) -> str:
    """Build MQTT topic for service command per 九井云 protocol.

    Topic format: /system/{productKey}/{deviceKey}/thing/service/{serviceName}
    """
    return f"/system/{product_key}/{device_key}/thing/service/{service_name}"


def build_command_payload(service_name: str, params: Dict[str, Any], cmd_id: Optional[str] = None) -> str:
    """Build JSON payload for service command.

    Format per 九井云 documentation:
    {
        "id": "唯一id",
        "version": "1.0.0",
        "params": {...},
        "method": "thing.service.{serviceName}"
    }
    """
    import json
    payload = {
        "id": cmd_id or str(uuid.uuid4()),
        "version": "1.0.0",
        "params": params,
        "method": f"thing.service.{service_name}"
    }
    return json.dumps(payload)