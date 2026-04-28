"""Coefficient tables. service -> class_id -> (low, mode, high) triangular params."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import IO


@dataclass(frozen=True)
class CoefficientTable:
    """Per-service per-class triangular coefficients."""

    table: Mapping[str, Mapping[int, tuple[float, float, float]]]

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Mapping[int, tuple[float, float, float]]],
    ) -> CoefficientTable:
        validate(data)
        frozen: dict[str, dict[int, tuple[float, float, float]]] = {
            service: {
                int(cls_id): (float(p[0]), float(p[1]), float(p[2]))
                for cls_id, p in by_class.items()
            }
            for service, by_class in data.items()
        }
        return cls(table=frozen)

    @classmethod
    def from_csv(cls, path: str | Path | IO[str]) -> CoefficientTable:
        """Read a long-format CSV with columns: service, class_id, low, mode, high."""
        import csv

        if isinstance(path, (str, Path)):
            with open(path, encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
        else:
            rows = list(csv.DictReader(path))

        out: dict[str, dict[int, tuple[float, float, float]]] = {}
        for row in rows:
            service = row["service"].strip()
            class_id = int(row["class_id"])
            params = (float(row["low"]), float(row["mode"]), float(row["high"]))
            out.setdefault(service, {})[class_id] = params
        return cls.from_dict(out)

    def services(self) -> list[str]:
        return list(self.table.keys())

    def classes(self, service: str) -> list[int]:
        return list(self.table[service].keys())

    def params(self, service: str, class_id: int) -> tuple[float, float, float]:
        return self.table[service][class_id]


def validate(data: Mapping[str, Mapping[int, tuple[float, float, float]]]) -> None:
    """Raise ValueError on any malformed coefficient row."""
    if not data:
        raise ValueError("CoefficientTable cannot be empty.")
    for service, by_class in data.items():
        if not isinstance(service, str) or not service:
            raise ValueError(f"Service name must be a non-empty string, got {service!r}.")
        if not by_class:
            raise ValueError(f"Service {service!r} has no class entries.")
        for class_id, params in by_class.items():
            if len(params) != 3:
                raise ValueError(
                    f"Service {service!r} class {class_id!r}: "
                    f"expected (low, mode, high), got {params!r}."
                )
            low, mode, high = params
            if not (low <= mode <= high):
                raise ValueError(
                    f"Service {service!r} class {class_id!r}: "
                    f"require low <= mode <= high, got ({low}, {mode}, {high})."
                )
