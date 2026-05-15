#!/usr/bin/env python3
import argparse
import json
import time
import sys
import uuid
import random
sys.path.insert(0, "scripts/test_data")
from generate_property_post import build_property_post, get_mqtt_topic


def update_realtime_fields(msg: dict) -> dict:
    msg["id"] = str(uuid.uuid4())
    if "MobileNetwork1" in msg["params"]:
        rsrp = random.randint(-100, -50)
        msg["params"]["MobileNetwork1"]["value"]["RSRP"] = str(rsrp)
    if "CPU" in msg["params"]:
        cpu = round(random.uniform(0.1, 0.9), 2)
        msg["params"]["CPU"]["value"] = str(cpu)
    if "UseMemory" in msg["params"]:
        mem = round(random.uniform(0.3, 0.8), 2)
        msg["params"]["UseMemory"]["value"] = str(mem)
    return msg


def main():
    parser = argparse.ArgumentParser(description="持续发送设备数据流")
    parser.add_argument("--product-key", "-pk", default="test-product")
    parser.add_argument("--device-key", "-dk", default="stream-test-device")
    parser.add_argument("--interval", "-i", type=int, default=5, help="发送间隔（秒）")
    parser.add_argument("--duration", "-d", type=int, default=0, help="持续时长（秒），0表示无限")
    parser.add_argument("--mqtt-bin", default="mosquitto_pub", help="MQTT publish 命令")
    parser.add_argument("--host", default="localhost", help="MQTT Broker 主机")
    parser.add_argument("--port", type=int, default=1883, help="MQTT Broker 端口")
    args = parser.parse_args()
    topic = get_mqtt_topic(args.product_key, args.device_key)
    print(f"Starting stream: topic={topic} interval={args.interval}s")
    print(f"Press Ctrl+C to stop")
    start_time = time.time()
    count = 0
    try:
        while True:
            msg = build_property_post(args.product_key, args.device_key, include_fields=None)
            msg = update_realtime_fields(msg)
            payload = json.dumps(msg, ensure_ascii=False)
            cmd = f'{args.mqtt_bin} -h {args.host} -p {args.port} -t "{topic}" -m \'{payload}\''
            print(f"[{count+1}] {cmd[:80]}...")
            os.system(cmd)
            count += 1
            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\nStopped. Total sent: {count}")
    print(f"Done. Total messages sent: {count}")


if __name__ == "__main__":
    import os
    main()