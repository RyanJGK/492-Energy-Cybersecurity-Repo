from __future__ import annotations

import json
import logging
import os
import socket
import struct
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

try:
    import dpkt  # lightweight pcap/packet parsing
except Exception:  # pragma: no cover - optional dependency
    dpkt = None  # type: ignore

from schemas import OTProtocolFrame  # reuse schema for normalization

from .dissectors.modbus import parse_modbus
from .dissectors.dnp3 import parse_dnp3
from .dissectors.iec104 import parse_iec104
from .dissectors.iec61850 import parse_iec61850


class KafkaProducer:
    def __init__(self, brokers: str, topic: str, logger: Optional[logging.Logger] = None):
        self.brokers = brokers
        self.topic = topic
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        # Placeholder: integrate confluent_kafka.Producer with acks=all in production

    def produce(self, key: str, value: str) -> None:
        # Placeholder stub; replace with real Kafka producer
        self.logger.debug("produce: key=%s len=%s", key, len(value))

    def flush(self) -> None:
        pass


class OTCollector:
    def __init__(self, interface: str, producer: KafkaProducer, logger: Optional[logging.Logger] = None):
        self.interface = interface
        self.producer = producer
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        if dpkt is None:
            raise RuntimeError("dpkt library is required for packet parsing")

        # Using pcap file reading for testability; replace with live capture via libpcap/pyshark in prod
        pcap_path = os.getenv("PCAP_PATH")
        if pcap_path:
            with open(pcap_path, "rb") as f:
                pcap = dpkt.pcap.Reader(f)
                for ts, buf in pcap:
                    self._handle_packet(ts, buf)
        else:
            self.logger.warning("Live capture not implemented in this stub. Provide PCAP_PATH env var.")

    def _handle_packet(self, ts: float, buf: bytes) -> None:
        try:
            eth = dpkt.ethernet.Ethernet(buf)
            if not isinstance(eth.data, dpkt.ip.IP):
                return
            ip = eth.data
            src_ip = socket.inet_ntoa(ip.src)
            dst_ip = socket.inet_ntoa(ip.dst)

            if isinstance(ip.data, dpkt.tcp.TCP):
                tcp = ip.data
                sport, dport = tcp.sport, tcp.dport
                payload = bytes(tcp.data or b"")

                if sport == 502 or dport == 502:  # Modbus/TCP
                    frame = parse_modbus(payload, src_ip, dst_ip)
                    if frame:
                        self._emit(frame)
                elif sport in (20000,) or dport in (20000,):  # DNP3 TCP
                    frame = parse_dnp3(payload, src_ip, dst_ip)
                    if frame:
                        self._emit(frame)
                elif sport in (2404,) or dport in (2404,):  # IEC 60870-5-104
                    frame = parse_iec104(payload, src_ip, dst_ip)
                    if frame:
                        self._emit(frame)
                elif sport in (102,) or dport in (102,):  # IEC 61850 MMS
                    frame = parse_iec61850(payload, src_ip, dst_ip)
                    if frame:
                        self._emit(frame)
            # TODO: Add UDP-based protocols as needed
        except Exception as exc:
            self.logger.exception("Packet handling error: %s", exc)

    def _emit(self, frame: OTProtocolFrame) -> None:
        key = frame.protocol
        value = frame.to_json()
        self.producer.produce(key=key, value=value)
