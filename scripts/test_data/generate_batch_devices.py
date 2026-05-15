#!/usr/bin/env python3
import argparse
import json
import uuid
import sys
import os
import random
from datetime import datetime
sys.path.insert(0, "scripts/test_data")
from generate_property_post import build_property_post, get_mqtt_topic


def generate_batch_device_data(count: int, prefix: str) -> list:
    devices = []
    for i in range(count):
        dk = f"{prefix}-{i+1:03d}"
        pk = "test-product-batch"
        msg = build_property_post(pk, dk, include_fields=None)
        msg["id"] = str(uuid.uuid4())
        topic = get_mqtt_topic(pk, dk)
        devices.append({"product_key": pk, "device_key": dk, "topic": topic, "payload": msg})
    return devices


def main():
    parser = argparse.ArgumentParser(description="批量生成多设备测试数据")
    parser.add_argument("--count", "-c", type=int, default=10, help="设备数量")
    parser.add_argument("--prefix", "-p", default="batch-device", help="设备前缀")
    parser.add_argument("--output-dir", "-o", default="scripts/test_data/output", help="输出目录")
    parser.add_argument("--format", "-f", choices=["mqtt", "json", "both"], default="mqtt")
    args = parser.parse_args()
    devices = generate_batch_device_data(args.count, args.prefix)
    os.makedirs(args.output_dir, exist_ok=True)
    if args.format in ("mqtt", "both"):
        mqtt_file = os.path.join(args.output_dir, "batch_mqtt.sh")
        with open(mqtt_file, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("# Auto-generated batch MQTT publish script\n\n")
            for d in devices:
                payload = json.dumps(d["payload"], ensure_ascii=False)
                f.write(f'echo "Publishing {d["device_key"]}..."\n')
                f.write(f'mosquitto_pub -t "{d["topic"]}" -m \'{payload}\'\n')
            f.write('echo "Done."\n')
        os.chmod(mqtt_file, 0o755)
        print(f"MQTT script: {mqtt_file}")
    if args.format in ("json", "both"):
        json_file = os.path.join(args.output_dir, "batch_devices.json")
        with open(json_file, "w") as f:
            json.dump(devices, f, indent=2, ensure_ascii=False)
        print(f"JSON data: {json_file}")
    print(f"Generated {len(devices)} device records.")


if __name__ == "__main__":
    main()