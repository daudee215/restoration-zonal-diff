"""Vector zone -> raster mask helpers (optional rasterio + shapely + fiona path)."""

from __future__ import annotations

from typing import Any


def rasterize_zones(
    zones_path: str,
    *,
    id_field: str,
    reference: Any,
    nodata: int = -1,
) -> Any:
    """Rasterise zones_path onto the grid of reference using id_field as the burn value."""
    try:
        import fiona
        import rasterio.features
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "rasterize_zones requires the [io] extras: pip install restoration-zonal-diff[io]"
        ) from exc

    shapes: list[tuple[Any, int]] = []
    with fiona.open(zones_path) as src:
        for feat in src:
            zid = int(feat["properties"][id_field])
            shapes.append((feat["geometry"], zid))

    return rasterio.features.rasterize(
        shapes,
        out_shape=reference.shape,
        transform=reference.transform,
        fill=nodata,
        dtype="int32",
    )
