"""End-to-end integration test on a 100-pixel synthetic grid covering 3 classes,
2 zones, 2 scenarios, 3 services, and 1,000 Monte Carlo draws.
"""

from __future__ import annotations

import numpy as np

from restoration_zonal_diff import CoefficientTable, diff_scenarios


def _make_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    baseline = rng.integers(1, 4, size=(10, 10)).astype(np.int32)
    # Scenario A converts every class-1 pixel to class-2.
    scenario_a = baseline.copy()
    scenario_a[scenario_a == 1] = 2
    # Scenario B converts every class-3 pixel to class-1.
    scenario_b = baseline.copy()
    scenario_b[scenario_b == 3] = 1
    zones = np.where(np.arange(100).reshape(10, 10) < 50, 1, 2).astype(np.int32)
    return baseline, scenario_a, scenario_b, zones


def test_two_scenarios_three_services() -> None:
    baseline, scenario_a, scenario_b, zones = _make_grid()
    table = CoefficientTable.from_dict(
        {
            "carbon": {1: (10.0, 12.0, 14.0), 2: (5.0, 7.0, 9.0), 3: (1.0, 2.0, 3.0)},
            "habitat": {1: (0.4, 0.5, 0.6), 2: (0.6, 0.7, 0.8), 3: (0.2, 0.3, 0.4)},
            "flood": {1: (3.0, 4.0, 5.0), 2: (1.0, 2.0, 3.0), 3: (0.5, 1.0, 1.5)},
        },
    )

    df = diff_scenarios(
        baseline=baseline,
        scenarios={"path-A": scenario_a, "path-B": scenario_b},
        zones=zones,
        coefficients=table,
        n_draws=1000,
        seed=42,
    )

    # Rows: 2 scenarios * 3 services * 2 zones = 12.
    assert len(df) == 12

    # Sanity: pathway A converts class-1 -> class-2; carbon coefficient drops 12 -> 7,
    # so per-pixel delta should be negative on average.
    a_carbon = df[(df["scenario"] == "path-A") & (df["service"] == "carbon")]
    assert (a_carbon["delta_mean"] < 0).all()

    # Sanity: pathway B converts class-3 -> class-1; carbon coefficient rises 2 -> 12,
    # so per-pixel delta should be positive on average.
    b_carbon = df[(df["scenario"] == "path-B") & (df["service"] == "carbon")]
    assert (b_carbon["delta_mean"] > 0).all()

    # CI bounds bracket the mean.
    for _, row in df.iterrows():
        assert row["delta_p2_5"] <= row["delta_mean"] <= row["delta_p97_5"]
