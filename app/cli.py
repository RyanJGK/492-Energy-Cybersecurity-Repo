from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from app.sim.feeder import FeederSim

app = typer.Typer(add_completion=False, help="Run OT/DER feeder simulations with clean output.")
console = Console()


def _results_table(title: str, rows: List[Dict[str, Any]]) -> Table:
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("step", justify="right")
    table.add_column("p_kw_limit", justify="right")
    table.add_column("v_min_pu", justify="right")
    table.add_column("v_max_pu", justify="right")
    table.add_column("line_loading_max_pct", justify="right")
    table.add_column("notes")

    for idx, row in enumerate(rows, start=1):
        vmin = row["v_min_pu"]
        vmax = row["v_max_pu"]
        load = row["line_loading_max_pct"]
        note_parts: List[str] = []
        vmin_str = f"[green]{vmin:.3f}[/]" if vmin >= 0.95 else f"[red]{vmin:.3f}[/]"
        vmax_str = f"[green]{vmax:.3f}[/]" if vmax <= 1.05 else f"[red]{vmax:.3f}[/]"
        load_str = f"[green]{load:.1f}[/]" if load <= 100.0 else f"[red]{load:.1f}[/]"
        if vmin < 0.95:
            note_parts.append("low voltage")
        if vmax > 1.05:
            note_parts.append("over voltage")
        if load > 100.0:
            note_parts.append("overload")
        if "note" in row and row["note"]:
            note_parts.append(str(row["note"]))
        table.add_row(
            str(idx),
            f"{row.get('p_kw_limit', '')}",
            vmin_str,
            vmax_str,
            load_str,
            ", ".join(note_parts),
        )
    return table


@app.command()
def powerflow(
    network: str = typer.Option("ieee13", help="Network: ieee13 | ieee34 | ieee123"),
) -> None:
    """Run a single power flow and print summary."""
    try:
        sim = FeederSim(network)
        results = sim.run_power_flow()
    except Exception as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(code=1)

    table = _results_table("Power Flow", [results | {"p_kw_limit": "-"}])
    console.print(table)


@app.command()
def curtail(
    p_kw_limit: float = typer.Argument(..., min=0, help="PV active power limit (kW) applied to all sgens"),
    network: str = typer.Option("ieee13", help="Network: ieee13 | ieee34 | ieee123"),
) -> None:
    """Simulate curtailment by setting PV p to the given kW limit and run power flow."""
    try:
        sim = FeederSim(network)
        sim.set_pv_p(p_kw_limit / 1000.0)
        results = sim.run_power_flow()
    except Exception as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(code=1)

    table = _results_table("Curtailment", [results | {"p_kw_limit": p_kw_limit}])
    console.print(table)


@app.command()
def scenario(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Path to scenario JSON"),
    network: str = typer.Option("ieee13", help="Network: ieee13 | ieee34 | ieee123"),
    export: Optional[Path] = typer.Option(None, help="Optional path to write JSON results"),
) -> None:
    """Run a multi-step scenario of curtailments and print a summary table."""
    try:
        data = json.loads(Path(path).read_text())
        steps: List[Dict[str, Any]]
        if isinstance(data, dict) and "steps" in data:
            steps = list(data["steps"])  # type: ignore[assignment]
        elif isinstance(data, list):
            steps = data  # type: ignore[assignment]
        else:
            console.print("[red]Invalid scenario format. Provide an array or an object with 'steps'.")
            raise typer.Exit(code=2)

        sim = FeederSim(network)
        rows: List[Dict[str, Any]] = []
        for step in steps:
            p_kw_limit = float(step.get("p_kw_limit", 0))
            note = step.get("note")
            sim.set_pv_p(p_kw_limit / 1000.0)
            res = sim.run_power_flow()
            rows.append(res | {"p_kw_limit": p_kw_limit, "note": note})

        table = _results_table("Scenario Results", rows)
        console.print(table)

        if export is not None:
            export.write_text(json.dumps(rows, indent=2))
            console.print(f"[green]Results written to[/] {export}")
    except Exception as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(code=1)


@app.command()
def api(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
) -> None:
    """Run the FastAPI server."""
    try:
        import uvicorn

        uvicorn.run("app.main:app", host=host, port=port, reload=reload)
    except Exception as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(code=1)


def main() -> None:
    app()
