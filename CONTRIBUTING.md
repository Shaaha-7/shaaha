# Contributing to Shaaha

## Setup

```bash
git clone https://github.com/Shaaha-7/shaaha.git
cd shaaha
pip install -e ".[dev,default]"
pytest tests/ -v
```

## Adding a new backend to an existing domain

Backends live in one place: the `REGISTRY` dict in
[`src/shaaha/registry.py`](src/shaaha/registry.py). Add a `Backend(...)`
entry to the relevant domain's list:

```python
"dataframe": [
    Backend("polars", "polars", weight=90, tags=["large_data", "fast"]),
    Backend("your_lib", "your_lib", weight=75, tags=["your_tag"]),
    ...
],
```

- `weight` decides priority when multiple candidates are installed -
  higher wins. Look at neighboring entries in the same domain to gauge
  a reasonable value.
- Set `gpu_preferred=True` only if the library specifically benefits from
  a GPU. These backends are automatically de-prioritized below the
  domain's standard-tier backends when no GPU is present (see
  `Registry.best_backend` and `shaaha.diagnose()` to see why) - don't
  try to work around that by inflating `weight` instead.
- If your library's public API differs from the domain's conventional
  one (the way Pillow's needed `shaaha/wrappers/image_pillow.py` to look
  like the domain's expected shape), add an adapter module under
  `src/shaaha/wrappers/` and reference it via `adapter="your_module"`.
- Run `shaaha.diagnose("<domain>")` after adding an entry to see exactly
  how it scores against the existing candidates on your machine.

## Adding a new domain

Add a new top-level key to `REGISTRY` with an ordered list of
`Backend(...)` candidates, then add a row to the "Supported Domains"
table in `README.md`.

## Tests

- `tests/test_shaaha.py`, `tests/test_shaaha_v2.py` - unit tests per module.
- `tests/test_domain_contracts.py` - behavioural contracts for whatever
  backend naturally resolves for a domain (no `force_backend`). If you add
  a domain or backend, prefer adding a contract test here over asserting
  which specific backend wins - that's expected to vary by machine.
- `tests/test_readme_examples.py` - mirrors README.md's own examples.
  **If you change a documented example, update the matching test in the
  same commit** - this file exists specifically because a README example
  broke in production once already (see `CHANGELOG.md`, 2.0.2) while every
  other test stayed green.

Before opening a PR: `pytest tests/ -v` should pass, and if your change
touches routing/scoring, run `shaaha diagnose` against a couple of
domains to sanity-check the output makes sense.

## Reporting bugs / requesting features

Use the issue templates under `.github/ISSUE_TEMPLATE/`.
