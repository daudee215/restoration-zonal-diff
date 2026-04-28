# ADR-0001 — Streaming, single-sweep MC zonal-diff over raster windows

Status: Accepted (2026-04-28)
Owner: Daud Tasleem

## Context

Nature restoration assessment under the EU Nature Restoration Regulation (and similar regional frameworks) needs ecosystem service value (ESV) deltas between baseline and one or more scenario rasters, aggregated to reporting zones (NUTS3, sub-basins, parcels), with explicit confidence bands. The dominant uncertainty source is benefit-transfer coefficient uncertainty: TEEB and ESVD report low / mode / high per service per biome.

We need to compute, for every (zone, scenario, service), the mean and 95 % credible interval of `delta = scenario_ESV - baseline_ESV`.

## Decision

Single-sweep streaming reduction over raster windows. For each window:

1. Read the baseline and scenario class rasters and the prebuilt zone-id raster.
2. For each class C present, find unique zones Z and pixel counts via `np.bincount` on the inverse map of `np.unique`.
3. Add `n_pix * draws[service][C]` (vector of length `n_draws`) to a running per-(service, zone) accumulator.

After the sweep, compute `delta = scenario_sum - baseline_sum` per (service, zone) and reduce across draws to mean + percentiles.

Memory is `O(zones * draws * services)`. Raster size is unbounded by RAM.

## Rejected alternatives

### Alt A — Repeated invocation of `rasterstats.zonal_stats`

Rejected. Each invocation reads the raster fully and repeats the vector–raster intersection. For `N` scenarios and `M` Monte Carlo draws this is `N*M` reads. On a 14 GB raster with `N=6, M=2000` this is intractable. Even a generous reuse of cached features cannot avoid the full re-read per draw because draws change pixel values, not zones.

### Alt B — Dask cluster fan-out, one task per draw

Rejected for v0.1. The scheduling overhead of `M` tasks (typically 1,000–10,000) dominates the cost on the 100 MB–10 GB single-machine workloads we target. For multi-tile mosaics on a real cluster, a Dask backend is the right answer; that lands in v0.2 as an opt-in.

### Alt C — PostGIS raster `ST_SummaryStats` per draw

Rejected. Same per-draw recomputation cost as Alt A, plus DB round-trips. Reasonable if the user has the rasters in PostGIS already, but the library should not require a database.

### Alt D — Pre-compute per-zone class histograms; reduce analytically

Considered. With per-zone class histograms `h[zone][class]` and per-(service, class) draws `d[service][class]`, the per-(zone, draw) sum is `sum_c h[zone][c] * d[service][c]`. This is what we do in spirit, except we accumulate streamingly so the histogram never has to be materialised in full.

## Consequences

- Single sweep per scenario raster, regardless of `n_draws`.
- Memory bound is small and predictable.
- The kernel is pure numpy; no C extension build dependencies.
- We do not handle reprojection on read; callers must align rasters first. v0.2 will add `rioxarray.reproject_match`.

## Validation

- Reference correctness against an in-memory numpy double-loop on small inputs (asserted to <1e-9 absolute) — see `tests/unit/test_streamer.py::test_accumulate_window_against_naive_loop`.
- End-to-end on a 100-pixel synthetic grid covering 3 classes, 2 zones, 2 scenarios, 3 services — see `tests/integration/test_pipeline.py`.
- Benchmark on a 100k-pixel synthetic raster — see `benchmarks/test_bench.py`.
