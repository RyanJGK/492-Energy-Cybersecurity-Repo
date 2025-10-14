from __future__ import annotations

import json
import os

from confluent_kafka import Consumer

from ot_collector.ot_tracking_agent import OTTrackingAgent


def main():
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    topic = os.getenv("OT_TOPIC", "ot-network-events")
    c = Consumer({
        "bootstrap.servers": brokers,
        "group.id": "lab.ot-tracking-agent.v1",
        "auto.offset.reset": "earliest",
    })
    c.subscribe([topic])

    agent = OTTrackingAgent()

    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        event = json.loads(msg.value())
        # Construct frame-like object
        from schemas import OTProtocolFrame
        frame = OTProtocolFrame(**event)
        alerts = agent.ingest_frame(frame)
        for a in alerts:
            print(f"ALERT: {a.severity} {a.rule} {a.message} {a.details}")


if __name__ == "__main__":
    main()
