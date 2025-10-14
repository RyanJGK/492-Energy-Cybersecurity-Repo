from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from schemas import OTProtocolFrame


# Simplified Modbus/TCP parsing: MBAP (7 bytes) + PDU
# Function code is first byte of PDU

def parse_modbus(payload: bytes, src_ip: str, dst_ip: str) -> Optional[OTProtocolFrame]:
    if len(payload) < 8:
        return None
    # MBAP header: Transaction ID (2), Protocol ID (2), Length (2), Unit ID (1)
    unit_id = payload[6]
    pdu = payload[7:]
    if not pdu:
        return None
    func_code = pdu[0]
    addr = None
    value = None
    # Read Holding Registers (3), Read Input Registers (4), Write Single Register (6), Write Multiple Registers (16)
    if len(pdu) >= 3:
        addr = int.from_bytes(pdu[1:3], "big")
    # For Write Single Register (6), value is next 2 bytes
    if func_code == 6 and len(pdu) >= 5:
        value = str(int.from_bytes(pdu[3:5], "big"))
    ts = datetime.now(timezone.utc)
    return OTProtocolFrame(
        protocol="modbus",
        src_ip=src_ip,
        dst_ip=dst_ip,
        func_code=str(func_code),
        addr=addr,
        value=value,
        session_id=f"{src_ip}->{dst_ip}",
        timestamp=ts,
    )
