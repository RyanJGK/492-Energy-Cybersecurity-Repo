from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from schemas import OTProtocolFrame


# Very simplified IEC 61850 MMS (IEC 61850 uses MMS over TCP/102; GOOSE is L2 and not parsed here)

def parse_iec61850(payload: bytes, src_ip: str, dst_ip: str) -> Optional[OTProtocolFrame]:
    if len(payload) < 1:
        return None
    # Heuristic: treat as MMS application PDU
    func = "mms"
    ts = datetime.now(timezone.utc)
    return OTProtocolFrame(
        protocol="iec61850",
        src_ip=src_ip,
        dst_ip=dst_ip,
        func_code=str(func),
        addr=None,
        value=None,
        session_id=f"{src_ip}->{dst_ip}",
        timestamp=ts,
    )
