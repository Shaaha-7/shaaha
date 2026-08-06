# Shaaha

> **One import. Best backend. Always.**

[![PyPI version](https://badge.fury.io/py/shaaha.svg)](https://pypi.org/project/shaaha/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/Shaaha-7/shaaha/actions/workflows/ci.yml/badge.svg)](https://github.com/Shaaha-7/shaaha/actions/workflows/ci.yml)

**Shaaha** is a Python meta-dispatcher library. Instead of memorising which
library is fastest, whether your system has a GPU, or whether a colleague has
`polars` installed — you write `import shaaha.dataframe` and Shaaha figures it
out for you, silently, at the moment you actually use it.

On top of that dispatcher, Shaaha includes an optional AI layer (natural
-language task execution, code review, plain-English explanations) that runs
against the Claude API when you provide a key, and falls back to rule-based
behaviour when you don't.

---

## The Problem Shaaha Solves

| Problem | Without Shaaha | With Shaaha |
|---------|---------------|-------------|
| **Dependency hell** | `try: import cupy except: import numpy` everywhere | `import shaaha.math` |
| **GPU/CPU branching** | Manual `torch.cuda.is_available()` checks | Automatic |
| **Large vs small data** | You pick polars or pandas | Shaaha picks for you |
| **Team differences** | Code breaks on colleagues' machines | Zero config |
| **Library upgrades** | Rewriting code when switching backends | Proxy API stays the same |
| **Silent breakage** | A missing method just crashes | Self-healer falls back and tells you |

---

## Install

```bash
pip install shaaha                      # zero dependencies
pip install "shaaha[default]"           # numpy, pandas, pillow, sklearn, matplotlib
pip install "shaaha[science]"           # full scientific stack
pip install "shaaha[gpu]"               # CUDA / GPU stack
pip install "shaaha[dashboard]"         # + flask, for shaaha.dashboard()
```

`pip install shaaha` on its own pulls in nothing beyond Shaaha itself — every
backend is opt-in through the extras above (or whatever you already have
installed).

---

## Quick Start

```python
import shaaha

# ── DataFrames ─────────────────────────────────────────────────────────────
import shaaha.dataframe as df
# Shaaha picks polars (large data) or pandas (small) automatically
data = df.read_csv("data.csv")

# ── Math / Arrays ──────────────────────────────────────────────────────────
import shaaha.math as sm
# On a GPU machine → cupy / jax. On CPU → numpy.
arr = sm.array([1, 2, 3, 4, 5])
result = sm.sqrt(arr)

# ── Machine Learning ───────────────────────────────────────────────────────
import shaaha.ml as ml
# GPU available → torch. Otherwise → scikit-learn / xgboost, whichever
# actually has the class you're calling (see "Self-Healing" below).
model = ml.LinearRegression()

# ── Image Processing ───────────────────────────────────────────────────────
import shaaha.image as img
# OpenCV if installed, else Pillow — same API either way.
image = img.open("photo.jpg")

# ── NLP ────────────────────────────────────────────────────────────────────
import shaaha.nlp as nlp
# HuggingFace Transformers → spaCy → NLTK (whichever is installed)

# ── Check what's running ───────────────────────────────────────────────────
print(shaaha.status())
# {'version': '2.0.2', 'cuda_available': False, 'selected_backends': {...}, ...}
```

---

## How It Works

Shaaha uses **PEP 302 Import Hooks** (`sys.meta_path`) to intercept Python's
import machinery *before* it looks for physical files.

```
import shaaha.math
       │
       ▼
ShaahafFinder (sys.meta_path[0])
       │  domain = "math"
       ▼
   Router.resolve("math")
       │  checks: CUDA? → No. numpy installed? → Yes.
       ▼
  ProxyModule wrapping numpy
       │
       ▼
  shaaha.math.array  →  numpy.array
```

The `ProxyModule` is lazy — **nothing is imported until you access an attribute**.
Initial `import shaaha` adds ~0ms to your startup time.

Run `shaaha diagnose` (or `shaaha.diagnose()` from Python) at any point to see
this decision made transparent — every candidate backend for a domain, whether
it's installed, its effective score, and which one actually wins on your
machine right now:

```
$ shaaha diagnose ml
  ml
    → sklearn        installed=yes  score= 70  eligible
      xgboost        installed=yes  score= 85  eligible
      torch          installed=yes  score= 40  eligible (capped 95->40: gpu_preferred but no GPU to exploit)
```

For just the plain list of what's currently importable, without the scoring
breakdown: `shaaha.available_backends("ml")`.

---

## Self-Healing

Picking the highest-scored backend isn't always enough on its own — `torch`
doesn't implement `LinearRegression`, `xgboost` doesn't either. If the
resolved backend is missing the attribute you called, Shaaha searches the
remaining candidates for one that actually has it, switches to that one, and
always tells you:

```
⚠️  [Shaaha] 'xgboost' failed on attribute 'LinearRegression' → switched to 'sklearn'.
   To suppress this warning: import shaaha; shaaha.suppress_warnings = True
```

The switch is cached, so it only happens once per domain per process — later
calls go straight to the backend that actually worked.

---

## AI-Powered Features

These three are optional and read `ANTHROPIC_API_KEY` from the environment
(or an explicit `api_key=` argument). Without a key, each one automatically
falls back to rule-based behaviour instead of failing.

```python
# Natural-language task execution
shaaha.agent("load sales.csv, find the top 10 products, and plot a bar chart")
# Plans the task (via Claude, or a rule-based fallback planner), executes
# each step, and writes shaaha_report.md.

# Code review / rewrite suggestions
shaaha.optimize_file("my_old_script.py")
# Flags slow patterns (raw pandas/numpy imports, iterrows() loops) and
# proposes shaaha-backed replacements. Every rewrite is checked against
# Python's own compiler before it's ever shown or applied — a change that
# would produce invalid syntax is reported as a finding instead of
# corrupting your file.

# Plain-English explanation of library choices
shaaha.explain("my_script.py", output="report.md")
```

> **Security note:** `shaaha.agent()` executes the generated plan via
> `exec()` with your full process privileges, whether that plan came from
> the Claude API or the offline fallback planner. Only point it at prompts
> and files you trust; don't run it against untrusted input in a shared or
> multi-tenant environment.

---

## Adaptive Learning

Shaaha times every backend operation locally and remembers what's actually
fastest on your machine (`~/.shaaha/profile.json`), nudging future routing
decisions as more data comes in.

```python
shaaha.status()          # current confidence + per-domain recommendations
shaaha.reset_learning()  # clear all learned data
```

Share what your machine has learned with a teammate, or pull in theirs:

```python
shaaha.share_profile("my_profile.json")
shaaha.import_profile("teammate.json")
shaaha.sync("http://team-server:8080")   # optional, if you're running one
```

---

## Dashboard & CLI

```python
shaaha.dashboard()   # opens http://127.0.0.1:7842 — backends chosen, speed history
```

```bash
shaaha status                # environment + brain status, as JSON
shaaha diagnose [domain]     # why each backend would (or wouldn't) be picked
shaaha list-backends [domain]
shaaha dashboard [--port PORT] [--no-browser]
```

---

## Safety Guard

Before trusting a switch between two backends for correctness-sensitive work,
verify they actually agree:

```python
shaaha.safe_mode(True)
shaaha.safe_call("math", "sqrt", data)
# ✅ Results match within tolerance. Safe to switch from 'jax' to 'numpy'.
# — or —
# ⚠️  Results DIFFER between 'jax' and 'numpy'. Switch NOT applied.
```

---

## Configuration

```python
import shaaha

shaaha.configure(
    prefer_gpu=True,        # Use GPU backends when available (default: True)
    auto_install=False,     # Offer to pip-install missing best backends
    log_level="WARNING",    # 'DEBUG' to see routing decisions
    force_backend={         # Override routing for specific domains
        "math": "numpy",    # Always use numpy even if cupy is installed
    }
)
```

---

## Supported Domains

| `shaaha.<domain>` | Best backend | Fallbacks |
|-------------------|-------------|-----------|
| `shaaha.math`     | cupy / jax  | torch → numpy |
| `shaaha.dataframe`| polars      | modin → pandas → dask |
| `shaaha.ml`       | torch       | xgboost → lightgbm → sklearn |
| `shaaha.image`    | cv2         | PIL / pillow |
| `shaaha.nlp`      | transformers| spacy → nltk |
| `shaaha.viz`      | plotly      | altair → seaborn → matplotlib |
| `shaaha.stats`    | statsmodels | scipy → sklearn |
| `shaaha.http`     | httpx       | requests → urllib3 |
| `shaaha.json`     | orjson      | ujson → json (stdlib) |

"Best backend" is a base priority, not an unconditional pick — GPU-preferred
entries (cupy, jax, torch) only get their boost when a GPU is actually
present; on a CPU-only machine the standard entry (numpy, sklearn, ...) wins
by default. `shaaha diagnose <domain>` shows the live scoring.

---

## Plugin System

Register a custom backend at runtime — no code changes or PR needed. It's
persisted to `~/.shaaha/plugins.json` and reloaded automatically on your next
`import shaaha`:

```python
shaaha.register_backend("dataframe", "vaex", "vaex", priority=88)
shaaha.list_backends("dataframe")
```

For a backend you want built into Shaaha itself for everyone, see
[Contributing](#contributing) below instead.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. Short version —
adding a backend to an existing domain is a few lines in `src/shaaha/registry.py`:

```python
"dataframe": [
    Backend("vaex", "vaex", weight=85, tags=["large_data", "out-of-core"]),
    # ... existing entries
]
```

Add a wrapper in `src/shaaha/wrappers/` if the library's API needs adapting
to match the domain's conventional shape, then open a Pull Request.

---

## Project Architecture

```
shaaha/
├── src/shaaha/
│   ├── __init__.py       # Registers sys.meta_path hook
│   ├── importer.py       # PEP 302 Finder + Loader
│   ├── router.py         # Decision engine (picks the winner)
│   ├── registry.py       # Library weights, domain mappings, diagnose()
│   ├── environment.py    # Hardware & dependency probe
│   ├── proxy.py          # Lazy proxy module system
│   ├── healer.py         # Self-healing fallback on missing attributes
│   ├── brain.py          # Adaptive learning (local timing history)
│   ├── installer.py      # Optional auto-pip-install
│   ├── agent.py          # Natural-language task execution (exec()-based)
│   ├── rewriter.py       # Code review / rewrite suggestions
│   ├── explainer.py      # Plain-English explainer
│   ├── dashboard.py      # Local web dashboard
│   ├── plugins.py        # Runtime backend registration
│   ├── collab.py         # Profile export/import/sync
│   ├── safety.py         # Cross-backend equivalence checks
│   ├── cli.py            # `shaaha` console script
│   ├── _llm.py           # Shared Claude API helper
│   └── wrappers/         # Unified API adapters per backend
├── tests/
├── .github/workflows/     # CI: OS/Python matrix, self-healer cascade, zero-dep install
├── pyproject.toml         # PEP 621 metadata
├── CHANGELOG.md
├── CONTRIBUTING.md
└── README.md
```

---

## License

MIT © Shabeer Ahamed
