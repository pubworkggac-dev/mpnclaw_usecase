"""九井云 IoT device simulator.

Simulates a CPE/路由器 device that:
1. Connects to MQTT broker using device credentials
2. Subscribes to service command topics
3. Receives and prints commands (does not actually execute)
4. Periodically publishes property/post telemetry (conforming to 九井云 protocol)
5. Publishes acknowledgement replies to service commands

Usage:
    python scripts/simulate_device.py --product-key pk --device-key dk --broker tcp://localhost:1883
    python scripts/simulate_device.py --product-key pk --device-key dk --broker tcp://localhost:1883 --interval 30
"""
import argparse
import json
import logging
import time
import uuid
import random
import threading

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("device-simulator")


class DeviceSimulator:
    """Simulates a 九井云 IoT device."""

    # 九井云物模型属性字段（完整定义，符合协议文档）
    PROPERTY_FIELDS = {
        "DeviceID": {"value": "SN-DEVICE-001"},
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
                "SINA": "-8"
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
                "Mode1": "802.11n",
                "IP1": "192.168.1.1",
                "Status2": 1,
                "Mode2": "802.11ac",
                "IP2": "192.168.2.1"
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

    def __init__(self, product_key: str, device_key: str, broker: str,
                 username: str = None, password: str = None,
                 property_interval: int = 30):
        self.product_key = product_key
        self.device_key = device_key
        self.broker = broker
        self.username = username
        self.password = password
        self.property_interval = property_interval
        self.client = None
        self._connected = False
        self._property_thread: threading.Thread | None = None

    def start(self):
        cid = f"sim-{self.device_key}-{uuid.uuid4().hex[:8]}"
        self.client = mqtt.Client(client_id=cid)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        if self.username:
            self.client.username_pw_set(self.username, self.password)

        host, port = self._parse_broker(self.broker)
        logger.info(f"Connecting to {host}:{port} as {cid}")
        self.client.connect(host, port, keepalive=60)
        self.client.loop_forever()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"Connected. Subscribing to service commands...")
            self._connected = True
            topic = f"/system/{self.product_key}/{self.device_key}/thing/service/+"
            client.subscribe(topic)
            logger.info(f"Subscribed: {topic}")

            topic_property = f"/system/{self.product_key}/{self.device_key}/thing/property/post"
            client.subscribe(topic_property)
            logger.info(f"Subscribed: {topic_property}")

            # 启动周期性 property/post 上报线程
            self._property_thread = threading.Thread(
                target=self._property_post_loop,
                daemon=True,
                name="property-post"
            )
            self._property_thread.start()
        else:
            logger.error(f"Connection failed: rc={rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        logger.warning(f"Disconnected (rc={rc}). Reconnecting...")
        self._connected = False

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"=== RECEIVED COMMAND on {msg.topic} ===")
            logger.info(f"  Method: {payload.get('method', 'N/A')}")
            logger.info(f"  ID: {payload.get('id', 'N/A')}")
            logger.info(f"  Params: {json.dumps(payload.get('params', {}), ensure_ascii=False)}")

            method = payload.get("method", "")
            if method.startswith("thing.service."):
                service_name = method.split(".")[-1]
                self._send_reply(service_name, payload.get("id"))

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def _property_post_loop(self):
        """周期性上报物模型属性（符合九井云协议，每隔 interval 秒发送一次）"""
        while self._connected:
            self._publish_property_post()
            time.sleep(self.property_interval)

    def _build_property_post_payload(self) -> dict:
        """构建符合九井云协议的物模型属性上报 payload"""
        from datetime import datetime
        params = {}
        for field, value in self.PROPERTY_FIELDS.items():
            if field == "OnlineInfo":
                params[field] = {"value": {"DeviceTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}
            elif field == "CPU":
                params[field] = {"value": str(round(random.uniform(0.1, 0.9), 2))}
            elif field == "UseMemory":
                params[field] = {"value": str(round(random.uniform(0.3, 0.8), 2))}
            elif field == "ModomIMEI":
                params[field] = {"value": f"862{random.randint(100000000000, 999999999999)}"}
            elif isinstance(value, dict) and "value" in value and isinstance(value["value"], dict):
                # 深拷贝
                params[field] = {"value": dict(value["value"])}
            else:
                params[field] = dict(value)

        # 随机化 MobileNetwork1 的 RSRP 模拟真实信号波动
        if "MobileNetwork1" in params:
            rsrp = random.randint(-100, -50)
            params["MobileNetwork1"]["value"]["RSRP"] = str(rsrp)

        return {
            "id": str(uuid.uuid4()),
            "version": "1.0",
            "sys": {"ack": 0},
            "params": params,
            "method": "thing.property.post"
        }

    def _publish_property_post(self):
        """发布物模型属性到 MQTT broker"""
        topic = f"/system/{self.product_key}/{self.device_key}/thing/property/post"
        payload = self._build_property_post_payload()
        payload_str = json.dumps(payload, ensure_ascii=False)
        self.client.publish(topic, payload_str)
        logger.info(f"[PROPERTY POST] topic={topic}")
        logger.info(f"[PROPERTY POST] payload={payload_str[:200]}...")

    def _send_reply(self, service_name: str, cmd_id: str | None):
        reply_topic = f"/system/{self.product_key}/{self.device_key}/thing/service/{service_name}_reply"
        reply = {
            "code": 200,
            "data": {
                "Result": "OK",
                "Code": "0",
                "Time": str(int(time.time())),
            },
            "id": cmd_id,
            "message": "success",
            "version": "1.0"
        }
        self.client.publish(reply_topic, json.dumps(reply))
        logger.info(f"  [REPLY] sent to {reply_topic}: {json.dumps(reply, ensure_ascii=False)}")

    @staticmethod
    def _parse_broker(broker: str):
        if "://" in broker:
            parts = broker.split("://", 1)[1].split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 1883
        elif ":" in broker:
            host, port = broker.rsplit(":", 1)
            port = int(port)
        else:
            host = broker
            port = 1883
        return host, port


def main():
    parser = argparse.ArgumentParser(description="九井云 device simulator")
    parser.add_argument("--product-key", default="test-product", help="Product key")
    parser.add_argument("--device-key", default="test-device-001", help="Device key")
    parser.add_argument("--broker", default="tcp://localhost:1883", help="MQTT broker URL")
    parser.add_argument("--username", default=None, help="MQTT username")
    parser.add_argument("--password", default=None, help="MQTT password")
    parser.add_argument("--interval", type=int, default=30,
                        help="Property/post publish interval in seconds (default: 30)")
    args = parser.parse_args()

    sim = DeviceSimulator(
        product_key=args.product_key,
        device_key=args.device_key,
        broker=args.broker,
        username=args.username,
        password=args.password,
        property_interval=args.interval,
    )
    sim.start()


if __name__ == "__main__":
    main()