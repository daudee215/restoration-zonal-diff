import numpy as np
import pytest

from restoration_zonal_diff import CoefficientTable, diff_scenarios


def test_diff_scenarios_columns_and_rows() -> None:
    baseline = np.array([[1, 1], [2, 2]], dtype=np.int32)
    scenario = np.array([[2, 2], [2, 2]], dtype=np.int32)
    zones = np.array([[1, 1], [1, 1]], dtype=np.int32)
    table = CoefficientTable.from_dict(
        {"carbon": {1: (10.0, 10.0, 10.0), 2: (3.0, 3.0, 3.0)}},
    )

    df = diff_scenarios(
        baseline=baseline,
        scenarios={"path-A": scenario},
        zones=zones,
        coefficients=table,
        n_draws=128,
        seed=0,
    )
    assert list(df.columns) == [
        "zone_id",
        "scenario",
        "service",
        "delta_mean",
        "delta_p2_5",
        "delta_p97_5",
        "pixels",
    ]
    assert len(df) == 1
    row = df.iloc[0]
    # zone 1: baseline {1,1,2,2} -> 2*10 + 2*3 = 26; scenario {2,2,2,2} -> 4*3 = 12; delta = -14.
    # All draws are constants (low==mode==high) so the mean is exactly -14 and CI bounds match.
    assert row["zone_id"] == 1
    assert row["scenario"] == "path-A"
    assert row["service"] == "carbon"
    assert abs(row["delta_mean"] + 14.0) < 1e-9
    assert abs(row["delta_p2_5"] + 14.0) < 1e-9
    assert abs(row["delta_p97_5"] + 14.0) < 1e-9
    assert row["pixels"] == 4


def test_diff_scenarios_rejects_shape_mismatch() -> None:
    baseline = np.zeros((2, 2), dtype=np.int32)
    bad = np.zeros((3, 2), dtype=np.int32)
    zones = np.zeros((2, 2), dtype=np.int32)
    table = CoefficientTable.from_dict({"x": {0: (1.0, 1.0, 1.0)}})
    with pytest.raises(ValueError, match="shape"):
        diff_scenarios(
            baseline=baseline,
            scenarios={"bad": bad},
            zones=zones,
            coefficients=table,
            n_draws=4,
            seed=0,
        )


def test_diff_scenarios_rejects_empty_scenarios() -> None:
    baseline = np.zeros((2, 2), dtype=np.int32)
    zones = np.zeros((2, 2), dtype=np.int32)
    table = CoefficientTable.from_dict({"x": {0: (1.0, 1.0, 1.0)}})
    with pytest.raises(ValueError, match="at least one"):
        diff_scenarios(
            baseline=baseline,
            scenarios={},
            zones=zones,
            coefficients=table,
            n_draws=4,
            seed=0,
        )
