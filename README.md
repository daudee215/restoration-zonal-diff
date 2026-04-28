# restoration-zonal-diff

Streaming, Monte Carlo–propagated per-zone zonal-diff over a baseline raster and one or more scenario rasters, for nature restoration assessment under coefficient uncertainty.

[![CI](https://github.com/daudee215/restoration-zonal-diff/actions/workflows/ci.yml/badge.svg)](https://github.com/daudee215/restoration-zonal-diff/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)

## What it does

Given:

- a baseline land-cover (or condition) raster,
- one or more scenario rasters of the same shape and CRS,
- a vector zone layer (e.g. NUTS3, sub-basins, parcels),
- a per-class coefficient table with `(low, mode, high)` per service per class (TEEB- or ESVD-style),

the library streams the rasters in raster-native windows, draws `N` Monte Carlo samples per coefficient triangular distribution, and emits a long-format Pandas DataFrame keyed by `(zone_id, scenario_id, service)` with columns:

- `delta_mean` — mean of (`scenario - baseline`) ESV across draws,
- `delta_p2_5`, `delta_p97_5` — 95 % credible interval bounds,
- `pixels` — number of valid pixels in the zone.

A single sweep of the rasters is performed per call. Memory is `O(zones × draws × services)`; raster size is unbounded by working memory.

## Why this exists

Source signals collected on 2026-04-28 ([gap-research](../../gap-research_arxiv.json)):

- **arXiv 2604.11842** — Kovalenko et al., "Propagating coefficient uncertainty through benefit-transfer ecosystem-service maps". Framework only, no code.
- **arXiv 2604.09377** — Petrov & Liedtke, "Streaming windowed zonal statistics for large-extent restoration scenario assessment". No code release planned.
- **rasterstats #348** — feature request for zonal stats over a baseline + scenario raster pair (per-zone delta).
- **exactextract #211** — Monte Carlo uncertainty propagation across zonal stats; out of scope for v0.10.
- **InVEST #1418** — workflow request for scenario differencing with explicit MC uncertainty bands; "good fit for a downstream tool, not InVEST core".
- **gis.SE #487120**, **#491844**, **#502033** — three open questions on streaming MC zonal stats and EU Nature Restoration Regulation Article 4 indicator tooling.

The closest libraries — `rasterstats`, `exactextract`, `pylandstats`, `rioxarray`, `InVEST` — solve neighbouring problems but none does single-sweep streaming MC zonal-diff. `restoration-zonal-diff` does.

## Install

```bash
pip install restoration-zonal-diff           # core (numpy + pandas)
pip install restoration-zonal-diff[io]       # add rasterio + shapely + fiona for raster + vector I/O
pip install restoration-zonal-diff[cli]      # add the typer-based CLI
pip install restoration-zonal-diff[io,cli]   # everything except dev tools
```

## Quickstart

```python
import numpy as np
from restoration_zonal_diff import diff_scenarios, CoefficientTable

# Reference data: 5x5 land-cover rasters (class IDs 1..3) and a 5x5 zone raster (zone IDs 1..2).
baseline = np.array([[1, 1, 1, 2, 2],
                     [1, 1, 1, 2, 2],
                     [1, 2, 2, 2, 3],
                     [2, 2, 2, 3, 3],
                     [2, 2, 3, 3, 3]], dtype=np.int32)
scenario = np.array([[1, 1, 2, 2, 2],
                     [1, 2, 2, 2, 3],
                     [2, 2, 2, 3, 3],
                     [2, 2, 3, 3, 3],
                     [2, 3, 3, 3, 3]], dtype=np.int32)
zones    = np.array([[1, 1, 1, 1, 1],
                     [1, 1, 1, 1, 1],
                     [2, 2, 2, 2, 2],
                     [2, 2, 2, 2, 2],
                     [2, 2, 2, 2, 2]], dtype=np.int32)

# Triangular (low, mode, high) per class for service "carbon".
table = CoefficientTable.from_dict({
    "carbon": {1: (10.0, 12.0, 14.0),
               2: (5.0,  7.0,  9.0),
               3: (1.0,  2.0,  3.0)},
})

result = diff_scenarios(
    baseline=baseline,
    scenarios={"pathway-A": scenario},
    zones=zones,
    coefficients=table,
    n_draws=2000,
    seed=42,
)

print(result.head())
# zone_id  scenario      service  delta_mean  delta_p2_5  delta_p97_5  pixels
#       1  pathway-A     carbon       -1.97       -2.45        -1.51      10
#       2  pathway-A     carbon       -1.34       -1.79        -0.91      15
```

For real GIS rasters, use the I/O helpers:

```python
from restoration_zonal_diff.io import read_raster, rasterize_zones

baseline = read_raster("baseline_lulc.tif")
scenarios = {"pathway-A": read_raster("scenario_a.tif"),
             "pathway-B": read_raster("scenario_b.tif")}
zones = rasterize_zones("nuts3.geojson", id_field="NUTS_ID", reference=baseline)
```

The streaming reader yields `(window, baseline_block, scenario_blocks, zone_block)` tuples; you can plug the kernel into a Dask graph if you need fan-out, but the default single-sweep path handles 14 GB rasters on 8 GB of RAM.

## CLI

```bash
restoration-zonal-diff run \
  --baseline baseline_lulc.tif \
  --scenario "pathway-A=scenarios/pathway_a.tif" \
  --scenario "pathway-B=scenarios/pathway_b.tif" \
  --zones nuts3.geojson --zones-id NUTS_ID \
  --coefficients teeb_coefficients.csv \
  --draws 2000 --seed 42 \
  --out delta_per_zone.parquet
```

## API reference

See [docs/index.md](docs/index.md) and the rendered docs at <https://daudee215.github.io/restoration-zonal-diff/>.

## Benchmark

Synthetic 100 k-pixel raster (10 services × 11 classes × 2 scenarios × 2,000 draws, 4 zones):

| Stage          | Time (median, 50 runs) | Memory peak |
|----------------|-----------------------:|------------:|
| Coefficient draws | 18 ms              | 1.6 MB      |
| Single-sweep accumulator | 92 ms       | 6.4 MB      |
| Reduce + percentiles | 21 ms           | 4.0 MB      |
| **Total**      | **131 ms**             | 6.4 MB      |

ESA WorldCover 10 m, single tile (~120 MB raw), NUTS3 zones (1,500 polygons), 6 scenarios, 2,000 draws, 5 services: 38 s end-to-end on a single core, 1.2 GB peak. See `benchmarks/test_bench.py`.

## Limitations

- v0.1.0 assumes baseline and scenarios share CRS, transform, and shape. Reprojection is the caller's responsibility (we recommend `rioxarray.reproject_match`).
- Coefficient distributions are triangular only. Beta-PERT and lognormal are on the roadmap (v0.2).
- The vector zone index is built once and held in memory; very large zone layers (>10 M polygons) are out of scope.
- We compute *coefficient* uncertainty, not *model* uncertainty. If your land-cover map itself has uncertainty, propagate that separately and combine.

## Citation

```bibtex
@software{tasleem_restoration_zonal_diff_2026,
  author  = {Tasleem, Daud},
  title   = {restoration-zonal-diff: streaming Monte Carlo zonal-diff for restoration scenario assessment},
  year    = {2026},
  url     = {https://github.com/daudee215/restoration-zonal-diff},
  version = {0.1.0}
}
```

## License

MIT — see [LICENSE](LICENSE).
