# OT Collector Passive Placement

Design principles prioritize safety and read-only collection. No write paths back into the ICS network.

- SPAN/TAP in ICS zone: Mirror ports on distribution/core switches inside the OT zone.
- Data diode: One-way egress from OT to Monitoring. Collector sits on OT side, forwarder on IT side.
- Network TAP: Hardware tap with read-only monitoring port connected to collector.

Operational controls:
- Collector NICs configured without IP addresses when possible (RFMON/sniff mode only).
- Firewall rules prevent outbound connections except to Kafka broker segment via diode/allowlist.
- Kafka producer uses TLS/SASL; topic: `ot-network-events`; acks=all; min.insync.replicas=2.
- Health monitoring via separate management interface on isolated VLAN.
