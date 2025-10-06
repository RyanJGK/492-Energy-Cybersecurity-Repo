from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/info")
async def info() -> dict:
    return {"service": "ot-der-telemetry-sim", "description": "Simulation-first OT/DER API"}
