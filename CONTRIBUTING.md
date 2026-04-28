# Contributing

Thanks for considering a contribution.

## Dev setup

```bash
git clone https://github.com/daudee215/restoration-zonal-diff
cd restoration-zonal-diff
python -m venv .venv && source .venv/bin/activate   # or PowerShell equivalent
pip install -e ".[io,cli,dev]"
pre-commit install
```

## Quality gates (must pass locally before opening a PR)

```bash
pytest -q
ruff check . && ruff format --check .
mypy --strict src
mkdocs build --strict
pip-audit
```

The same gates run in CI on every PR. PRs that fail any hard-fail gate will not be merged.

## ADRs

Any architectural change (algorithm, data structure, dependency) requires a new ADR under `docs/adr/`. See `docs/adr/0001-architecture.md` for the format.

## Changelog

Add a one-line entry under `## Unreleased` in `CHANGELOG.md` (created on first release).
