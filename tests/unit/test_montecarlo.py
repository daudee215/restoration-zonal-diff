import numpy as np
import pytest

from restoration_zonal_diff.coefficients import CoefficientTable
from restoration_zonal_diff.montecarlo import triangular_draws


def _table() -> CoefficientTable:
    return CoefficientTable.from_dict(
        {"carbon": {1: (10.0, 12.0, 14.0), 2: (5.0, 7.0, 9.0)}},
    )


def test_triangular_draws_shape() -> None:
    draws = triangular_draws(_table(), n_draws=128, seed=0)
    assert set(draws.keys()) == {"carbon"}
    assert set(draws["carbon"].keys()) == {1, 2}
    assert draws["carbon"][1].shape == (128,)
    assert draws["carbon"][2].shape == (128,)


def test_triangular_draws_bounds() -> None:
    draws = triangular_draws(_table(), n_draws=4096, seed=7)
    v = draws["carbon"][1]
    assert v.min() >= 10.0 and v.max() <= 14.0
    # Mode of (10, 12, 14) -> mean = (10 + 12 + 14) / 3 = 12.0; loose check.
    assert abs(v.mean() - 12.0) < 0.2


def test_triangular_draws_reproducible() -> None:
    a = triangular_draws(_table(), n_draws=256, seed=42)
    b = triangular_draws(_table(), n_draws=256, seed=42)
    np.testing.assert_array_equal(a["carbon"][1], b["carbon"][1])


def test_triangular_draws_zero_variance_class() -> None:
    table = CoefficientTable.from_dict({"x": {1: (5.0, 5.0, 5.0)}})
    draws = triangular_draws(table, n_draws=10, seed=0)
    np.testing.assert_array_equal(draws["x"][1], np.full(10, 5.0))


def test_triangular_draws_rejects_bad_n() -> None:
    with pytest.raises(ValueError):
        triangular_draws(_table(), n_draws=0, seed=0)
