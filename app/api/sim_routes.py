from fastapi import APIRouter, HTTPException

from app.sim.feeder import FeederSim

sim_router = APIRouter(prefix="/simulate", tags=["simulate"])


@sim_router.get("/powerflow/{network}")
async def powerflow(network: str = "ieee13") -> dict:
    try:
        sim = FeederSim(network)
        results = sim.run_power_flow()
        return {"network": network, "results": results}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
