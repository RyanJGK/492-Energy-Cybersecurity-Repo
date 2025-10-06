from typing import Dict, Optional

try:
    import pandapower as pp  # type: ignore
    import pandapower.networks as pn  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pp = None
    pn = None

from app.models.settings import settings
from app.utils.logging import get_logger


logger = get_logger(__name__)


class FeederSim:
    """Simple wrapper around pandapower for IEEE test feeders.

    Security/ops: only enabled when settings.enable_simulation is True.
    """

    def __init__(self, network: str = "ieee13") -> None:
        if not settings.enable_simulation:
            raise RuntimeError("Simulation disabled by settings")
        if pp is None or pn is None:
            raise RuntimeError("pandapower not installed; install with extras: sim")
        self.network_name = network
        self.net = self._load_network(network)

    def _load_network(self, name: str):
        loaders = {
            "ieee13": pn.case_ieee13,
            "ieee34": pn.case_ieee34,
            "ieee123": pn.case_ieee123,
        }
        if name not in loaders:
            raise ValueError(f"Unsupported network: {name}")
        return loaders[name]()

    def run_power_flow(self) -> Dict[str, float]:
        pp.runpp(self.net)
        v_min = float(self.net.res_bus.vm_pu.min())
        v_max = float(self.net.res_bus.vm_pu.max())
        loading_max = float(self.net.res_line.loading_percent.max())
        return {"v_min_pu": v_min, "v_max_pu": v_max, "line_loading_max_pct": loading_max}

    def set_pv_p(self, p_mw: float) -> None:
        sgen_indices = self.net.sgen.index.tolist()
        for idx in sgen_indices:
            self.net.sgen.at[idx, "p_mw"] = p_mw
