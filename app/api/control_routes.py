from fastapi import APIRouter, HTTPException

from app.models.settings import settings
from app.models.telemetry import CurtailmentRequest
from app.services.policy import allow
from app.sim.feeder import FeederSim

control_router = APIRouter(prefix="/control", tags=["control"])


@control_router.post("/curtail")
async def curtail(req: CurtailmentRequest) -> dict:
    if not req.simulate or not settings.read_only_mode:
        # For safety, only support simulate=True under read-only default
        raise HTTPException(status_code=403, detail="controls limited to simulate-only in read_only_mode")

    if not await allow("control", {"device_id": req.device_id, "action": "curtail", "p_kw_limit": req.p_kw_limit}):
        raise HTTPException(status_code=403, detail="policy_denied")

    # Simulate effect on feeder by adjusting PV setpoint and running power flow
    sim = FeederSim("ieee13")
    sim.set_pv_p(req.p_kw_limit / 1000.0)  # kW -> MW
    results = sim.run_power_flow()
    return {"device_id": req.device_id, "effective_p_kw": req.p_kw_limit, "results": results}
