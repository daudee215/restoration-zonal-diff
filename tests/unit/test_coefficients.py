import io

import pytest

from restoration_zonal_diff.coefficients import CoefficientTable, validate


def test_from_dict_roundtrip() -> None:
    table = CoefficientTable.from_dict(
        {"carbon": {1: (10.0, 12.0, 14.0), 2: (5.0, 7.0, 9.0)}},
    )
    assert table.services() == ["carbon"]
    assert table.classes("carbon") == [1, 2]
    assert table.params("carbon", 1) == (10.0, 12.0, 14.0)


def test_validate_rejects_bad_order() -> None:
    with pytest.raises(ValueError, match="low <= mode <= high"):
        validate({"carbon": {1: (10.0, 14.0, 12.0)}})


def test_validate_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate({})


def test_validate_rejects_empty_service() -> None:
    with pytest.raises(ValueError, match="no class entries"):
        validate({"carbon": {}})


def test_from_csv() -> None:
    csv_text = (
        "service,class_id,low,mode,high\ncarbon,1,10,12,14\ncarbon,2,5,7,9\nhabitat,1,1,2,3\n"
    )
    table = CoefficientTable.from_csv(io.StringIO(csv_text))
    assert sorted(table.services()) == ["carbon", "habitat"]
    assert table.params("habitat", 1) == (1.0, 2.0, 3.0)
