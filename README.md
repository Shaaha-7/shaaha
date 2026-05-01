# Shaaha 🧠

> **One import. Best backend. Always.**

[![PyPI version](https://badge.fury.io/py/shaaha.svg)](https://pypi.org/project/shaaha/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/shaaha/shaaha/actions/workflows/test.yml/badge.svg)](https://github.com/shaaha/shaaha/actions)

**Shaaha** is a Python meta-dispatcher library. Instead of memorising which
library is fastest, whether your system has a GPU, or whether a colleague has
`polars` installed — you write `import shaaha.dataframe` and Shaaha figures it
out for you, silently, at the moment you actually use it.

---

## The Problem Shaaha Solves

| Problem | Without Shaaha | With Shaaha |
|---------|---------------|-------------|
| **Dependency hell** | `try: import cupy except: import numpy` everywhere | `import shaaha.math` |
| **GPU/CPU branching** | Manual `torch.cuda.is_available()` checks | Automatic |
| **Large vs small data** | You pick polars or pandas | Shaaha picks for you |
| **Team differences** | Code breaks on colleagues' machines | Zero config |
| **Library upgrades** | Rewriting code when switching backends | Proxy API stays the same |

---

## Install

```bash
pip install shaaha                      # zero dependencies
pip install "shaaha[default]"           # numpy, pandas, pillow, sklearn, matplotlib
pip install "shaaha[science]"           # full scientific stack
pip install "shaaha[gpu]"               # CUDA / GPU stack
```

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
# GPU available → torch. Otherwise → scikit-learn / xgboost.
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
# {'version': '1.0.0', 'cuda_available': False, 'selected_backends': {...}}
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

---

## Adding a New Backend (Contributing)

1. Open `src/shaaha/registry.py`
2. Add your backend to the relevant domain list:

```python
"dataframe": [
    Backend("vaex", "vaex", weight=85, tags=["large_data", "out-of-core"]),
    # ... existing entries
]
```

3. Optionally add a wrapper in `src/shaaha/wrappers/` if the API differs.
4. Open a Pull Request — that's it.

---

## Project Architecture

```
shaaha/
├── src/shaaha/
│   ├── __init__.py       # Registers sys.meta_path hook
│   ├── importer.py       # PEP 302 Finder + Loader
│   ├── router.py         # Decision engine (picks the winner)
│   ├── registry.py       # Library weights & domain mappings
│   ├── environment.py    # Hardware & dependency probe
│   ├── proxy.py          # Lazy proxy module system
│   ├── installer.py      # Optional auto-pip-install
│   └── wrappers/         # Unified API adapters per backend
├── tests/
│   └── test_shaaha.py    # 24 tests, 100% passing
├── pyproject.toml        # PEP 621 metadata
└── README.md
```

---

## For MSc Thesis

Shaaha implements three advanced CS concepts worth discussing in your thesis:

1. **Python Import Protocol (PEP 302/451)** — `sys.meta_path`, `MetaPathFinder`, `Loader`
2. **Proxy Design Pattern** — transparent delegation via `__getattr__` on a `ModuleType` subclass
3. **Context-Aware Dispatch** — weighted scoring with hardware-aware overrides

---

## License

MIT © Shaaha
