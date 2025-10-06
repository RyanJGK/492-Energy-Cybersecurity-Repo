from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class MeterTelemetry(BaseModel):
    kind: Literal["meter"] = "meter"
    voltage_v: Optional[float] = None
    current_a: Optional[float] = None
    real_power_kw: Optional[float] = None
    reactive_power_kvar: Optional[float] = None


class InverterTelemetry(BaseModel):
    kind: Literal["inverter"] = "inverter"
    p_kw: float
    q_kvar: float
    v_pu: Optional[float] = None
    status: Optional[Literal["on", "off", "fault"]] = None


class EVSETelemetry(BaseModel):
    kind: Literal["evse"] = "evse"
    charging_kw: float
    plugged_in: bool
    soc_pct: Optional[float] = None


DiscriminatedTelemetry = Annotated[
    Union[MeterTelemetry, InverterTelemetry, EVSETelemetry],
    Field(discriminator="kind"),
]


class TelemetryEnvelope(BaseModel):
    """Generic telemetry envelope with discriminated payload.

    Security: schema-validated to mitigate injection and malformed payloads.
    """

    device_id: str
    ts: datetime
    data: DiscriminatedTelemetry


class CurtailmentRequest(BaseModel):
    device_id: str
    p_kw_limit: float
    simulate: bool = True
    reason: Optional[str] = None
