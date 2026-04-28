# Roadmap

## v0.1.0 (current)

- Triangular coefficient distributions per class per service.
- Single-sweep streaming reduction over baseline + scenario rasters.
- Vector zone index via Shapely STRtree, rasterised once against the baseline grid.
- Long-format Parquet/CSV output with delta_mean, delta_p2_5, delta_p97_5, pixels.
- Typer CLI (`restoration-zonal-diff run`).
- Benchmark on a 100 k-pixel synthetic raster.
- Reference correctness vs an in-memory numpy double-loop on small inputs (<1e-9 absolute).

## v0.2.0 (next)

- Beta-PERT and lognormal coefficient distributions.
- Optional Dask backend for fan-out over multi-tile mosaics.
- Reprojection-on-read using `rioxarray.reproject_match`.
- CLI `validate` subcommand: check coefficient table sanity, raster CRS/transform alignment, zone coverage.
- COG-aware windowing: prefer block-aligned reads when the input raster is a Cloud Optimized GeoTIFF.

## v1.0.0 (stable goal)

- API freeze.
- Documented EU Nature Restoration Regulation indicator presets (Article 4 condition deltas, Article 7 connectivity deltas).
- Coupling with InVEST output rasters (named output recipes).
- Performance: 1 GB raster × 6 scenarios × 2,000 draws under 60 s on a single core.
