# restoration-zonal-diff

A streaming, Monte Carlo–propagated zonal-diff engine for nature restoration assessment.

## When to use

You have a baseline land-cover (or condition) raster, one or more scenario rasters, a vector zone layer, and a per-class coefficient table with `(low, mode, high)` values per service. You want per-zone deltas with credible intervals, in a single pass over the rasters.

## API surface

```python
from restoration_zonal_diff import (
    CoefficientTable,
    diff_scenarios,
    triangular_draws,
    accumulate_window,
    finalize,
)
```

- `CoefficientTable` — typed wrapper for `{service: {class_id: (low, mode, high)}}`.
- `triangular_draws(table, n_draws, seed)` — produce per-(service, class) coefficient draws.
- `accumulate_window(lulc, zones, draws, sums, counts)` — fold one raster window into running sums.
- `finalize(...)` — reduce running sums to per-(zone, scenario, service) deltas.
- `diff_scenarios(...)` — high-level one-call API.

See the [README](https://github.com/daudee215/restoration-zonal-diff#readme) for the worked quickstart.

## Architecture

See [ADR-0001](adr/0001-architecture.md).
