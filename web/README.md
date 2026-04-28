# web/

Static, single-file interactive demo for `restoration-zonal-diff`. Deployed to GitHub Pages by `.github/workflows/pages.yml` on every push to `main` that touches `web/`.

The demo runs a small JavaScript port of the streaming Monte Carlo zonal-diff algorithm so you can see how the credible-interval band shrinks as `n_draws` increases, and how editing the per-class TEEB coefficient triangles shifts the per-zone delta-ESV mean and 95 % CI.

It is not a substitute for the Python library — for real-extent rasters use `pip install restoration-zonal-diff[io,cli]` and the `restoration-zonal-diff run` CLI documented in the project README.

## Local preview

```bash
python -m http.server -d web 8000
# open http://localhost:8000
```
