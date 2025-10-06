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
        normalized = str(name).lower().replace("_", "").replace("-", "")

        # Map common IEEE aliases to pandapower networks
        alias_map = {
            "ieee13": "case_ieee13",
            "ieee34": "case_ieee34",
            "ieee123": "case_ieee123",
        }

        target_attr = alias_map.get(normalized, normalized)
        if not hasattr(pn, target_attr):
            available = sorted([n for n in dir(pn) if n.startswith("case_")])
            raise ValueError(
                f"Unsupported network: {name}. Try one of: ieee13, ieee34, ieee123 or pandapower: {available[:10]}..."
            )
        loader = getattr(pn, target_attr)
        return loader()

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
