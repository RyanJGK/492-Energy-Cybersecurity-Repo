from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from schemas import OTProtocolFrame


# Minimal DNP3 application layer indicator stub

def parse_dnp3(payload: bytes, src_ip: str, dst_ip: str) -> Optional[OTProtocolFrame]:
    if len(payload) < 2:
        return None
    func_code = payload[1]  # not accurate; placeholder for demo
    ts = datetime.now(timezone.utc)
    return OTProtocolFrame(
        protocol="dnp3",
        src_ip=src_ip,
        dst_ip=dst_ip,
        func_code=str(func_code),
        addr=None,
        value=None,
        session_id=f"{src_ip}->{dst_ip}",
        timestamp=ts,
    )
