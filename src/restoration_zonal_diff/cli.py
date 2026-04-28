"""Typer-based CLI. Activated via the [cli] extras."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _require_typer() -> Any:
    try:
        import typer

        return typer
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "The CLI requires the [cli] extras: pip install restoration-zonal-diff[cli]"
        ) from exc


typer = _require_typer()
app = typer.Typer(add_completion=False, help="Streaming MC zonal-diff for restoration scenarios.")


@app.command()
def run(
    baseline: Path = typer.Option(..., exists=True, readable=True),
    scenario: list[str] = typer.Option(..., "--scenario"),
    zones: Path = typer.Option(..., exists=True, readable=True),
    zones_id: str = typer.Option("zone_id", "--zones-id"),
    coefficients: Path = typer.Option(..., exists=True, readable=True),
    draws: int = typer.Option(1000, "--draws", min=1),
    seed: int = typer.Option(42, "--seed"),
    out: Path = typer.Option(..., "--out"),
) -> None:
    """Run a single-sweep MC zonal-diff and write out (Parquet if .parquet, else CSV)."""
    from restoration_zonal_diff.coefficients import CoefficientTable
    from restoration_zonal_diff.diff import diff_scenarios
    from restoration_zonal_diff.zones import rasterize_zones

    try:
        import rasterio
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "The CLI requires the [io] extras: pip install restoration-zonal-diff[io]"
        ) from exc

    table = CoefficientTable.from_csv(coefficients)
    pairs: dict[str, Any] = {}
    for spec in scenario:
        if "=" not in spec:
            raise typer.BadParameter(f"--scenario expects NAME=PATH, got {spec!r}")
        name, path = spec.split("=", 1)
        pairs[name.strip()] = path.strip()

    with rasterio.open(baseline) as base_src:
        base_arr = base_src.read(1)
        z_arr = rasterize_zones(str(zones), id_field=zones_id, reference=base_src)
        scen_arrs: dict[str, Any] = {}
        for name, path in pairs.items():
            with rasterio.open(path) as scen_src:
                scen_arrs[name] = scen_src.read(1)

    df = diff_scenarios(
        baseline=base_arr,
        scenarios=scen_arrs,
        zones=z_arr,
        coefficients=table,
        n_draws=draws,
        seed=seed,
    )

    if out.suffix.lower() == ".parquet":
        df.to_parquet(out, index=False)
    else:
        df.to_csv(out, index=False)
    typer.echo(f"wrote {len(df)} rows -> {out}")


if __name__ == "__main__":
    app()
