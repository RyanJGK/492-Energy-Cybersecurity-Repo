from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from schemas import OTProtocolFrame


# Very simplified IEC 60870-5-104 function code placeholder

def parse_iec104(payload: bytes, src_ip: str, dst_ip: str) -> Optional[OTProtocolFrame]:
    if len(payload) < 1:
        return None
    func_code = payload[0]
    ts = datetime.now(timezone.utc)
    return OTProtocolFrame(
        protocol="iec104",
        src_ip=src_ip,
        dst_ip=dst_ip,
        func_code=str(func_code),
        addr=None,
        value=None,
        session_id=f"{src_ip}->{dst_ip}",
        timestamp=ts,
    )
