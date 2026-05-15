#!/usr/bin/env python3
import argparse
import json
import uuid
import sys
sys.path.insert(0, "scripts/test_data")
from generate_property_post import build_property_post


JIUJINGYUN_SERVICES = {
    "SetDeviceName": {"DeviceName": "MyRouter"},
    "SetNTPConfig": {"NtpSwitch": "1", "NtpServer1": "pool.ntp.org", "NtpServer2": "time.google.com"},
    "SetUserInfo": {"OldUserName": "admin", "NewUserName": "admin2", "OldUserPassword": "oldpass", "NewUserPassword": "newpass", "NewReUserPassword": "newpass"},
    "DeviceReboot": {"Rule": "3", "Day": 1, "Week": 1, "Hour": 0, "Minutes": 0},
    "WANPPPOEConfig": {"Switch": "1", "GatewayHop": 1, "DNS": "8.8.8.8", "UserName": "user@example.com", "Password": "secret123", "Name": "WAN-PPPoE"},
    "WANSTATICConfig": {"Switch": "1", "GatewayHop": 1, "DNS": "8.8.8.8", "IPAddress": "10.0.0.100", "Mask": "255.255.255.0", "Gateway": "10.0.0.1", "Name": "WAN-Static"},
    "WANDHCPConfig": {"Switch": "1", "GatewayHop": 1, "DNS": "8.8.8.8", "Name": "WAN-DHCP"},
    "WANPriority": {"Interface": "nrWan", "Priority": 1},
    "LANConfig": {"Server": "192.168.0.1", "Mask": "255.255.255.0", "DHCPSwitch": "1", "DHCPStartIp": "192.168.0.100", "DHCPEndIp": "192.168.0.200", "LeaseTime": "24", "DNS": "8.8.8.8"},
    "MobileNetworkConfig": {"Id": "1", "Switch": "1", "APN": "internet", "AuthMethod": "0", "UserName": "", "Password": "", "VLANId": "", "SliceInfo": "", "DialProtocol": "1", "DataRoamingSwitch": "0", "PreferredNetworkMode": "AUTO", "IpAddress": "", "Mask": ""},
    "FiveGLANConfig": {"ID": "1", "Switch": "1", "APN": "internet", "AuthMethod": "0", "UserName": "", "Password": "", "VLANId": "", "SliceInfo": "", "IpAddress": "", "Mask": ""},
    "LockScreenLockCommunity": {"Function": "0", "ID": "1", "Scstype": "0", "Band": "", "FrequencyPoint": "", "CommunityID": ""},
    "AgentSwitch": {"AgentSwitch": "1"},
    "SetPostRoute": {"PostRouteSwitch": "1"},
    "SIMConfig": {"MainCardSelect": "1", "PINCard1": "", "PUKCard1": "", "BindSIMCard1": "0", "WantBindSIMCard1": "", "BindSIMCard2": "0", "WantBindSIMCard2": ""},
    "HotStandby": {"Switch": "0", "SerialNumber": "", "InterfaceNumber": "br-lan1", "Role": "MASTER", "VRID": "", "NodePriority": 100, "Password": "", "InspectionInterval": 30, "LogLevel": "0", "VirtualAddress": "", "DHCPSwitch": "0", "ServerAddress": "", "HeartbeatInterval": 5, "Timeout": 3, "Weight": 100, "TestSuccess": 3, "TestFail": 3},
    "NATForwardingConfig": [{"Action": "add", "Name": "web-server", "Protocol": "0", "OuteArea": "0", "ExternalPort": "8080", "InteArea": "1", "InternalIP": "192.168.0.100", "InternalPort": "80"}],
    "DMZ": {"Switch": "1", "InternalIp": "192.168.0.200"},
    "RestoreFactorySettings": {},
    "RebootDevice": {},
    "SetPING": {"Action": "1", "Address": "8.8.8.8"}
}


def build_service_command(product_key: str, device_key: str, service_name: str, params: dict | None = None) -> dict:
    if params is None:
        params = JIUJINGYUN_SERVICES.get(service_name, {})
    return {
        "id": str(uuid.uuid4()),
        "version": "1.0.0",
        "params": params,
        "method": f"thing.service.{service_name}"
    }


def get_service_topic(product_key: str, device_key: str, service_name: str) -> str:
    return f"/system/{product_key}/{device_key}/thing/service/{service_name}"


def main():
    parser = argparse.ArgumentParser(description="生成九井云服务命令消息")
    parser.add_argument("--product-key", "-pk", default="test-product")
    parser.add_argument("--device-key", "-dk", default="test-device-001")
    parser.add_argument("--service-name", "-s", required=True, choices=list(JIUJINGYUN_SERVICES.keys()))
    parser.add_argument("--params", "-p", default="{}", help="参数字典 JSON 字符串")
    parser.add_argument("--output-format", "-f", choices=["mqtt", "json"], default="mqtt")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    params = json.loads(args.params) if args.params != "{}" else None
    msg = build_service_command(args.product_key, args.device_key, args.service_name, params)
    if args.output_format == "mqtt":
        topic = get_service_topic(args.product_key, args.device_key, args.service_name)
        payload = json.dumps(msg, indent=2 if args.pretty else None, ensure_ascii=False)
        print(f"Topic: {topic}")
        print(f"Payload: {payload}")
    else:
        print(json.dumps(msg, indent=2 if args.pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    main()