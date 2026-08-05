# Changelog

All notable changes to this project are documented here.

## [2.0.2] - Unreleased

Bug-fix release. Everything here was found by actually running the
README's own examples and the existing test suite in a realistic
environment (torch + xgboost + sklearn installed together, no GPU) rather
than by inspection alone.

### Fixed
- **Self-healer was never wired up.** `ProxyModule` accepted a `healer_cls`
  argument that both construction sites left as `None`, so the fallback
  behaviour documented in the README (Layer 5) could never fire.
  `shaaha.ml.LinearRegression()` — the Quick Start example — raised an
  uncaught `AttributeError` on any machine with torch installed alongside
  sklearn, since torch has no such attribute and nothing caught it.
- **`try_fallback` could switch to a backend that also lacked the
  attribute** (e.g. torch → xgboost, when only sklearn actually has
  `LinearRegression`). It now checks candidates against the same
  flat-map-aware lookup the proxy itself uses before committing to one.
- **`_build_flat_map` could crash mid-walk.** Walking `xgboost`'s
  submodules imports `xgboost.testing`, which raises pytest's `Skipped` -
  deliberately a `BaseException` subclass, not `Exception`, so it survived
  the existing `except Exception` guards.
- **GPU-preferred backends (torch, jax) outranked numpy/sklearn even with
  no GPU present**, because their base registry weight alone was higher.
  `shaaha.math.array(...)` silently returned a `torch._numpy` shim object
  instead of a real `numpy.ndarray` on any GPU-less machine with torch
  installed. Now `gpu_preferred` backends only get their score boost when
  a GPU is actually available; otherwise they're capped below the
  standard tier.
- **The code rewriter could emit invalid Python.** The `iterrows()` rules
  did whole-file regex substitution of a mid-statement code fragment for
  a bare comment, which corrupts the enclosing `for` statement. These
  rules are now report-only, and a `compile()` check now guards every
  rewrite (rule-based or LLM-sourced) before it's shown or applied.
- **Crashed on the default Windows console.** Every module prints emoji
  status messages; on the default cp1252 codepage that raised
  `UnicodeEncodeError` on first call. `shaaha` now forces UTF-8 stdout/
  stderr at import time.
- **The PIL adapter was dead code.** `registry.py` pointed at
  `shaaha.wrappers.image_pillow`, but no `shaaha/wrappers` package
  existed - it silently `ImportError`-fell-back to raw PIL. The package
  now exists and the adapter actually loads.
- **`__version__` was hardcoded and stale** (`"2.0.0"` while `pyproject.toml`
  said `2.0.1`). Now sourced from package metadata at import time.
- Removed the `anthropic` optional dependency, which was declared in three
  extras groups but never imported anywhere (the AI layers use `urllib`
  directly by design, to stay dependency-light).
- Fixed `pyproject.toml` project URLs, which all pointed at a
  `github.com/shaaha/shaaha` placeholder that was never registered; they
  now point at the real repository.
- Added the `LICENSE` file, referenced by the README and `pyproject.toml`
  but never committed.

### Added
- `shaaha.diagnose()` — prints a transparent, per-backend score breakdown
  for one or all domains, so "why did shaaha pick X" doesn't require
  reading source.
- `shaaha` console script (`shaaha status`, `shaaha diagnose [domain]`,
  `shaaha list-backends [domain]`, `shaaha dashboard`).
- `tests/test_readme_examples.py` - executes every runnable section of
  README.md as a real test, so a regression in the documented examples
  fails CI instead of shipping.
- `tests/test_domain_contracts.py` - behavioural contracts for naturally
  routed (non-forced) domains.
- `.github/workflows/ci.yml` - test matrix across OS/Python versions, a
  dedicated job exercising the multi-backend self-healer cascade, and a
  dedicated job enforcing the zero-dependency install promise.
- `src/shaaha/_llm.py` - single shared helper for the three near-identical
  raw Claude API calls in `agent.py`/`rewriter.py`/`explainer.py`
  (previously each hardcoded its own copy of the model ID).

### Changed
- `shaaha.dashboard()`'s Flask app construction was split out into
  `_build_app()` so the dashboard can be tested with `test_client()`
  instead of only being verifiable by hand in a browser.

## [2.0.1] - 2026-05-07
Initial 2.0.x patch release on PyPI.

## [2.0.0] - 2026-05-07
AI Agent, Adaptive Brain, Self-Healer, Dashboard, Safety Guard layers.

## [1.0.0] - 2026-05-01
Initial release.
