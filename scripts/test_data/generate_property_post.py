#!/usr/bin/env python3
"""
生成九井云格式的物模型属性上报消息（MQTT payload）。

用法：
    python generate_property_post.py --product-key test-product --device-key test-device-001 --include MobileNetwork1,CPU,UseMemory --output-format mqtt

输出：九井云标准格式的 MQTT payload JSON，可直接用于 mosquitto_pub -t '/system/{pk}/{dk}/thing/property/post' -m '{...}'
"""
import argparse
import json
import uuid
from datetime import datetime


# 九井云标准字段定义（物模型属性）
JIUJINGYUN_PROPERTY_FIELDS = {
    "DeviceID": {"value": "SN-DEFAULT-001"},
    "DeviceHWVersion": {"value": "1.0.2"},
    "DeviceSWVersion": {"value": "1.0.1"},
    "ModomVersion": {"value": "EC20CEFAGR06A10M1G"},
    "ModomModel": {"value": "Quectel EC20"},
    "ModomIMEI": {"value": "862647523456789"},
    "SIMCard1": {
        "value": {
            "Status": 1,
            "IMSI": "460001234567890",
            "ICCID": "89860123456789012345"
        }
    },
    "SIMCard2": {
        "value": {
            "Status": 0,
            "IMSI": "",
            "ICCID": ""
        }
    },
    "MobileNetwork1": {
        "value": {
            "Status": 1,
            "CommunityType": "LTE",
            "CommunityID": "0x1234ABCD",
            "CommunityFrequency": "1850",
            "RSRP": "-75",
            "IPV4": "192.168.1.100",
            "IPV6": "",
            "Dns1": "8.8.8.8",
            "Dns2": "8.8.4.4",
            "PingDelay": "32",
            "BAND": "B3",
            "PDP": "IP",
            "SINA": "15"
        }
    },
    "MobileNetwork2": {
        "value": {
            "Status": 0,
            "CommunityType": "",
            "CommunityID": "",
            "CommunityFrequency": "",
            "RSRP": "",
            "IPV4": "",
            "IPV6": "",
            "Dns1": "",
            "Dns2": "",
            "PingDelay": "",
            "BAND": "",
            "PDP": "",
            "SINA": ""
        }
    },
    "WLAN": {
        "value": {
            "Status1": 1,
            "Mode1": "802.11ac",
            "IP1": "192.168.1.101",
            "Status2": 1,
            "Mode2": "802.11ax",
            "IP2": "192.168.1.102"
        }
    },
    "LAN": {
        "value": {
            "IP": "192.168.0.1",
            "Status": "1",
            "MAC": "AA:BB:CC:DD:EE:FF"
        }
    },
    "CPU": {"value": "0.35"},
    "OnlineInfo": {"value": {"DeviceTime": ""}},
    "CPEModel": {"value": "CPE-Pro-5G"},
    "UseMemory": {"value": "0.58"},
    "ModuleTemperature": {"value": "45"},
    "PositionInfo": {
        "value": {
            "Longitude": "116.4074",
            "Latitude": "39.9042",
            "Height": "50",
            "Unit": "m"
        }
    },
    "DiskUsage": {"value": "0.42"},
    "WiredPort1Info": {
        "value": {
            "Port": "1",
            "ReceiveTraffic": "1024.56",
            "ReceiveRate": "10.5",
            "SendRate": "5.2",
            "SendTraffic": "512.34"
        }
    },
    "WiredPort2Info": {
        "value": {
            "Port": "2",
            "ReceiveTraffic": "0",
            "ReceiveRate": "0",
            "SendRate": "0",
            "SendTraffic": "0"
        }
    },
    "WiredPort3Info": {
        "value": {
            "Port": "3",
            "ReceiveTraffic": "0",
            "ReceiveRate": "0",
            "SendRate": "0",
            "SendTraffic": "0"
        }
    },
    "WiredPort4Info": {
        "value": {
            "Port": "4",
            "ReceiveTraffic": "0",
            "ReceiveRate": "0",
            "SendRate": "0",
            "SendTraffic": "0"
        }
    },
    "WiredPort5Info": {
        "value": {
            "Port": "5",
            "ReceiveTraffic": "0",
            "ReceiveRate": "0",
            "SendRate": "0",
            "SendTraffic": "0"
        }
    },
    "AirInterfaceLink1Info": {
        "value": {
            "Name": "5G-Link1",
            "TotalFlow": "2048.75",
            "PeakBandwidthUtilization": "850.3"
        }
    },
    "AirInterfaceLink2Info": {
        "value": {
            "Name": "5G-Link2",
            "TotalFlow": "0",
            "PeakBandwidthUtilization": "0"
        }
    },
    "GatewayTotalTraffic": {"value": "4096.50"}
}


def build_property_post(product_key: str, device_key: str, include_fields: list | None = None) -> dict:
    """构建九井云物模型属性上报消息"""
    params = {}

    available_fields = list(JIUJINGYUN_PROPERTY_FIELDS.keys())

    if include_fields:
        fields_to_include = [f for f in include_fields if f in available_fields]
    else:
        fields_to_include = available_fields

    for field in fields_to_include:
        params[field] = JIUJINGYUN_PROPERTY_FIELDS[field]

    # 更新时间相关字段
    if "OnlineInfo" in params:
        params["OnlineInfo"]["value"]["DeviceTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "id": str(uuid.uuid4()),
        "version": "1.0",
        "sys": {"ack": 0},
        "params": params,
        "method": "thing.property.post"
    }


def get_mqtt_topic(product_key: str, device_key: str) -> str:
    """获取九井云物模型属性上报的 MQTT topic"""
    return f"/system/{product_key}/{device_key}/thing/property/post"


def main():
    parser = argparse.ArgumentParser(description="生成九井云物模型属性上报消息")
    parser.add_argument("--product-key", "-pk", default="test-product", help="产品唯一标识")
    parser.add_argument("--device-key", "-dk", default="test-device-001", help="设备唯一标识")
    parser.add_argument("--include", "-i", default="", help="包含的字段，逗号分隔，如 MobileNetwork1,CPU,UseMemory")
    parser.add_argument("--output-format", "-f", choices=["mqtt", "json"], default="mqtt",
                        help="输出格式：mqtt（带topic+payload）或 json（仅payload）")
    parser.add_argument("--pretty", "-p", action="store_true", help="美化输出 JSON")

    args = parser.parse_args()

    include_fields = [f.strip() for f in args.include.split(",") if f.strip()] if args.include else None
    msg = build_property_post(args.product_key, args.device_key, include_fields)

    if args.output_format == "mqtt":
        topic = get_mqtt_topic(args.product_key, args.device_key)
        if args.pretty:
            payload = json.dumps(msg, indent=2, ensure_ascii=False)
        else:
            payload = json.dumps(msg, ensure_ascii=False)
        print(f"Topic: {topic}")
        print(f"Payload: {payload}")
    else:
        if args.pretty:
            print(json.dumps(msg, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(msg, ensure_ascii=False))


if __name__ == "__main__":
    main()