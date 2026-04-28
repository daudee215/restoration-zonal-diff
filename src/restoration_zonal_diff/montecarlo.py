"""Monte Carlo coefficient draws for benefit-transfer ecosystem service valuation."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from restoration_zonal_diff.coefficients import CoefficientTable

ServiceDraws = dict[int, NDArray[np.float64]]


def triangular_draws(
    table: CoefficientTable,
    n_draws: int,
    seed: int | None = None,
) -> dict[str, ServiceDraws]:
    """Draw n_draws triangular samples per (service, class)."""
    if n_draws <= 0:
        raise ValueError(f"n_draws must be > 0, got {n_draws}.")
    rng = np.random.default_rng(seed)

    out: dict[str, ServiceDraws] = {}
    for service in table.services():
        out[service] = {}
        for class_id in table.classes(service):
            low, mode, high = table.params(service, class_id)
            if low == high:
                out[service][class_id] = np.full(n_draws, fill_value=mode, dtype=np.float64)
            else:
                out[service][class_id] = rng.triangular(
                    left=low, mode=mode, right=high, size=n_draws
                ).astype(np.float64)
    return out
