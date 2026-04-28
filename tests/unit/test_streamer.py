import numpy as np
import pytest

from restoration_zonal_diff.coefficients import CoefficientTable
from restoration_zonal_diff.montecarlo import triangular_draws
from restoration_zonal_diff.streamer import (
    accumulate_window,
    empty_state,
    finalize,
)


def _setup() -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    baseline = np.array(
        [[1, 1, 2], [2, 2, 3], [3, 3, 1]],
        dtype=np.int32,
    )
    scenario = np.array(
        [[1, 2, 2], [2, 3, 3], [3, 3, 3]],
        dtype=np.int32,
    )
    zones = np.array(
        [[1, 1, 1], [1, 2, 2], [2, 2, 2]],
        dtype=np.int32,
    )
    table = CoefficientTable.from_dict(
        {"carbon": {1: (10.0, 12.0, 14.0), 2: (5.0, 7.0, 9.0), 3: (1.0, 2.0, 3.0)}},
    )
    draws = triangular_draws(table, n_draws=200, seed=11)
    return baseline, scenario, zones, draws


def test_accumulate_window_against_naive_loop() -> None:
    baseline, _, zones, draws = _setup()
    sums, counts = empty_state(["carbon"], n_draws=200)
    accumulate_window(baseline, zones, draws, sums, counts)

    # Naive reference: per zone, expected sum_per_draw = sum over pixels of draws[class]
    # Here we average each draw and check against a numpy-only recomputation.
    expected = {z: np.zeros(200) for z in (1, 2)}
    for r in range(baseline.shape[0]):
        for c in range(baseline.shape[1]):
            z = int(zones[r, c])
            cls = int(baseline[r, c])
            expected[z] += draws["carbon"][cls]

    for zone in (1, 2):
        np.testing.assert_allclose(
            sums["carbon"][zone],
            expected[zone],
            rtol=0,
            atol=1e-12,
        )

    # Pixel counts: zone 1 has 4 pixels (rows 0 plus (1,0)), zone 2 has 5 pixels.
    assert counts == {1: 4, 2: 5}


def test_finalize_computes_delta() -> None:
    baseline, scenario, zones, draws = _setup()
    sums_b, counts_b = empty_state(["carbon"], n_draws=200)
    sums_s, counts_s = empty_state(["carbon"], n_draws=200)
    accumulate_window(baseline, zones, draws, sums_b, counts_b)
    accumulate_window(scenario, zones, draws, sums_s, counts_s)

    rows = finalize(sums_b, {"path-A": sums_s}, counts_b, {"path-A": counts_s})
    by_zone = {(r["zone_id"], r["scenario"], r["service"]): r for r in rows}

    # Delta = scenario - baseline. We verify zone 1: baseline classes [1,1,1,2], scenario classes
    # [1,2,2,2]. So delta in classes is +1 for class 2 and -1 for class 1, and the scenario gains
    # class 2 contribution of (draws[c=2] - draws[c=1]) for one pixel; the rest cancel.
    delta_z1 = sums_s["carbon"][1] - sums_b["carbon"][1]
    expected_mean = float(delta_z1.mean())
    assert abs(by_zone[(1, "path-A", "carbon")]["delta_mean"] - expected_mean) < 1e-9


def test_accumulate_window_shape_mismatch() -> None:
    baseline = np.zeros((2, 2), dtype=np.int32)
    zones = np.zeros((3, 3), dtype=np.int32)
    sums, counts = empty_state(["carbon"], n_draws=4)
    with pytest.raises(ValueError, match="shape mismatch"):
        accumulate_window(
            baseline,
            zones,
            {"carbon": {0: np.zeros(4)}},
            sums,
            counts,
        )


def test_accumulate_window_empty_draws() -> None:
    baseline = np.zeros((2, 2), dtype=np.int32)
    zones = np.zeros((2, 2), dtype=np.int32)
    sums: dict = {}
    counts: dict = {}
    with pytest.raises(ValueError, match="non-empty"):
        accumulate_window(baseline, zones, {}, sums, counts)


def test_nodata_zone_excluded() -> None:
    baseline = np.array([[1, 1], [2, 2]], dtype=np.int32)
    zones = np.array([[1, -1], [-1, 2]], dtype=np.int32)
    table = CoefficientTable.from_dict({"x": {1: (1.0, 1.0, 1.0), 2: (2.0, 2.0, 2.0)}})
    draws = triangular_draws(table, n_draws=10, seed=0)
    sums, counts = empty_state(["x"], n_draws=10)
    accumulate_window(baseline, zones, draws, sums, counts, nodata_zone=-1)
    assert counts == {1: 1, 2: 1}
