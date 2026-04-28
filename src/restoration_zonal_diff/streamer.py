"""Streaming windowed accumulator for per-(zone, scenario, draw) ESV totals."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from numpy.typing import NDArray

from restoration_zonal_diff.montecarlo import ServiceDraws

Sums = dict[str, dict[int, NDArray[np.float64]]]
Counts = dict[int, int]


def empty_state(services: Iterable[str], n_draws: int) -> tuple[Sums, Counts]:
    """Initialise an empty (sums, counts) pair for a single raster sweep."""
    _ = n_draws  # carried for future schema validation
    sums: Sums = {service: {} for service in services}
    counts: Counts = {}
    return sums, counts


def accumulate_window(
    lulc: NDArray[np.integer],
    zones: NDArray[np.integer],
    draws: dict[str, ServiceDraws],
    sums: Sums,
    counts: Counts,
    nodata_zone: int = -1,
) -> None:
    """Add one raster window's contribution to the running per-(zone, draw) sums."""
    if lulc.shape != zones.shape:
        raise ValueError(f"lulc and zones shape mismatch: {lulc.shape} vs {zones.shape}.")
    if not draws:
        raise ValueError("draws must be non-empty.")

    services = list(draws.keys())
    classes = sorted({c for service_draws in draws.values() for c in service_draws})

    valid = zones != nodata_zone
    for class_id in classes:
        class_mask = (lulc == class_id) & valid
        if not class_mask.any():
            continue
        zones_here = zones[class_mask]
        unique_zones, inv = np.unique(zones_here, return_inverse=True)
        per_zone_count = np.bincount(inv, minlength=unique_zones.size)
        for k, zone_id in enumerate(unique_zones.tolist()):
            n_pix = int(per_zone_count[k])
            if n_pix == 0:
                continue
            counts[zone_id] = counts.get(zone_id, 0) + n_pix
            for service in services:
                vec = draws[service].get(class_id)
                if vec is None:
                    continue
                if zone_id not in sums[service]:
                    sums[service][zone_id] = np.zeros_like(vec)
                sums[service][zone_id] += vec * n_pix


def finalize(
    sums_baseline: Sums,
    sums_scenarios: dict[str, Sums],
    counts_baseline: Counts,
    counts_scenarios: dict[str, Counts],
    p_low: float = 2.5,
    p_high: float = 97.5,
) -> list[dict[str, float | int | str]]:
    """Reduce per-draw sums to per-(zone, scenario, service) delta percentiles."""
    rows: list[dict[str, float | int | str]] = []
    for scenario, sums_s in sums_scenarios.items():
        counts_s = counts_scenarios[scenario]
        services = set(sums_baseline.keys()) | set(sums_s.keys())
        for service in sorted(services):
            zones_union = set(sums_baseline.get(service, {}).keys()) | set(
                sums_s.get(service, {}).keys()
            )
            for zone in sorted(zones_union):
                base_vec = sums_baseline.get(service, {}).get(zone)
                scen_vec = sums_s.get(service, {}).get(zone)
                if base_vec is None and scen_vec is None:
                    continue
                if base_vec is None:
                    assert scen_vec is not None
                    base_vec = np.zeros_like(scen_vec)
                if scen_vec is None:
                    scen_vec = np.zeros_like(base_vec)
                delta = scen_vec - base_vec
                pixels = max(counts_baseline.get(zone, 0), counts_s.get(zone, 0))
                rows.append(
                    {
                        "zone_id": int(zone),
                        "scenario": str(scenario),
                        "service": str(service),
                        "delta_mean": float(delta.mean()),
                        "delta_p2_5": float(np.percentile(delta, p_low)),
                        "delta_p97_5": float(np.percentile(delta, p_high)),
                        "pixels": int(pixels),
                    }
                )
    return rows
