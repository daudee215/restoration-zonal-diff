"""High-level diff_scenarios API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from restoration_zonal_diff.coefficients import CoefficientTable
from restoration_zonal_diff.montecarlo import triangular_draws
from restoration_zonal_diff.streamer import accumulate_window, empty_state, finalize


def diff_scenarios(
    *,
    baseline: NDArray[np.integer],
    scenarios: Mapping[str, NDArray[np.integer]],
    zones: NDArray[np.integer],
    coefficients: CoefficientTable,
    n_draws: int = 1000,
    seed: int | None = None,
    nodata_zone: int = -1,
    p_low: float = 2.5,
    p_high: float = 97.5,
) -> pd.DataFrame:
    """Compute per-zone per-scenario per-service Monte Carlo ESV deltas."""
    if not scenarios:
        raise ValueError("scenarios must contain at least one entry.")
    for name, raster in scenarios.items():
        if raster.shape != baseline.shape:
            raise ValueError(
                f"scenario {name!r} shape {raster.shape} does not match baseline {baseline.shape}."
            )
    if zones.shape != baseline.shape:
        raise ValueError(f"zones shape {zones.shape} does not match baseline {baseline.shape}.")

    draws = triangular_draws(coefficients, n_draws=n_draws, seed=seed)

    sums_b: Any
    counts_b: Any
    sums_b, counts_b = empty_state(coefficients.services(), n_draws)
    accumulate_window(baseline, zones, draws, sums_b, counts_b, nodata_zone=nodata_zone)

    sums_scenarios: dict[str, Any] = {}
    counts_scenarios: dict[str, Any] = {}
    for name, raster in scenarios.items():
        sums_s, counts_s = empty_state(coefficients.services(), n_draws)
        accumulate_window(raster, zones, draws, sums_s, counts_s, nodata_zone=nodata_zone)
        sums_scenarios[name] = sums_s
        counts_scenarios[name] = counts_s

    rows = finalize(
        sums_b,
        sums_scenarios,
        counts_b,
        counts_scenarios,
        p_low=p_low,
        p_high=p_high,
    )
    return pd.DataFrame(
        rows,
        columns=[
            "zone_id",
            "scenario",
            "service",
            "delta_mean",
            "delta_p2_5",
            "delta_p97_5",
            "pixels",
        ],
    )
