from __future__ import annotations

import os
from ot_collector.ot_collector import OTCollector, KafkaProducer


def main():
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    topic = os.getenv("OT_TOPIC", "ot-network-events")
    producer = KafkaProducer(brokers=brokers, topic=topic)
    collector = OTCollector(interface=os.getenv("IFACE", "eth0"), producer=producer)
    collector.run()


if __name__ == "__main__":
    main()
