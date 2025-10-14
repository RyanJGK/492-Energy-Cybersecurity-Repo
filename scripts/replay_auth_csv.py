from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

from confluent_kafka import Producer


def delivery(err, msg):
    if err:
        print(f"Delivery failed: {err}")


def main(csv_path: str, topic: str = "auth-verification-events") -> None:
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    p = Producer({"bootstrap.servers": brokers, "acks": "all"})
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["type"] = row.get("type", "AuthVerificationRequested")
            if "timestamp" not in row:
                row["timestamp"] = datetime.now(timezone.utc).isoformat()
            p.produce(topic, key=row.get("user_id", ""), value=json.dumps(row), callback=delivery)
    p.flush()


if __name__ == "__main__":
    main(sys.argv[1])
