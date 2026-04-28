"""Pytest-benchmark suite. Run with: pytest --benchmark-only benchmarks/."""

from __future__ import annotations

import numpy as np
import pytest

from restoration_zonal_diff import CoefficientTable, diff_scenarios


@pytest.fixture
def workload() -> dict:
    rng = np.random.default_rng(0)
    n = 316
    baseline = rng.integers(1, 12, size=(n, n)).astype(np.int32)
    scenario_a = rng.integers(1, 12, size=(n, n)).astype(np.int32)
    scenario_b = rng.integers(1, 12, size=(n, n)).astype(np.int32)
    zones = (np.arange(n * n).reshape(n, n) // (n * n // 4) + 1).astype(np.int32)

    table_dict: dict = {}
    for service in ("carbon", "habitat", "flood", "water", "recreation"):
        table_dict[service] = {}
        for cls in range(1, 12):
            low = rng.uniform(0.1, 5.0)
            mode = low + rng.uniform(0.5, 3.0)
            high = mode + rng.uniform(0.5, 3.0)
            table_dict[service][cls] = (low, mode, high)
    table = CoefficientTable.from_dict(table_dict)
    return {
        "baseline": baseline,
        "scenarios": {"a": scenario_a, "b": scenario_b},
        "zones": zones,
        "coefficients": table,
    }


def test_bench_diff_scenarios(benchmark, workload):  # type: ignore[no-untyped-def]
    df = benchmark(
        lambda: diff_scenarios(
            baseline=workload["baseline"],
            scenarios=workload["scenarios"],
            zones=workload["zones"],
            coefficients=workload["coefficients"],
            n_draws=2000,
            seed=42,
        )
    )
    assert len(df) == 40
