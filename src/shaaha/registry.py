"""
shaaha.registry
===============
The "Knowledge Base" of Shaaha.

Each domain maps to an ordered list of candidate backends.
Backends are tried in order; the first importable one wins.
Weights encode quality: higher = preferred.

Community contributors should add new domains and backends here.
"""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger("shaaha.registry")


@dataclass
class Backend:
    """A single candidate backend for a domain."""
    name: str                        # pip/import name
    import_name: str                 # actual Python import (may differ, e.g. PIL vs pillow)
    weight: int                      # higher = preferred
    gpu_preferred: bool = False      # prefer when GPU detected
    requires_cuda: bool = False      # skip entirely if no CUDA
    requires_mps: bool = False       # skip entirely if no MPS
    adapter: Optional[str] = None    # wrapper class in shaaha.wrappers.<adapter>
    tags: list = field(default_factory=list)   # e.g. ['large_data', 'streaming']


# ---------------------------------------------------------------------------
# THE REGISTRY
# All community contributions live here.
# ---------------------------------------------------------------------------

REGISTRY: dict[str, list[Backend]] = {

    # ── DATAFRAME ──────────────────────────────────────────────────────────
    "dataframe": [
        Backend("polars",  "polars",  weight=90, tags=["large_data", "fast"]),
        Backend("modin",   "modin",   weight=80, tags=["large_data", "pandas_compat"]),
        Backend("pandas",  "pandas",  weight=70, tags=["small_data", "standard"]),
        Backend("dask",    "dask",    weight=60, tags=["streaming", "distributed"]),
    ],

    # ── MATH / ARRAY ───────────────────────────────────────────────────────
    "math": [
        Backend("cupy",    "cupy",    weight=95, gpu_preferred=True, requires_cuda=True),
        Backend("jax",     "jax",     weight=90, gpu_preferred=True, tags=["autodiff"]),
        Backend("torch",   "torch",   weight=85, gpu_preferred=True, tags=["tensor"]),
        Backend("numpy",   "numpy",   weight=70, tags=["standard"]),
    ],

    # ── IMAGE ──────────────────────────────────────────────────────────────
    "image": [
        Backend("cv2",     "cv2",     weight=90, tags=["computer_vision", "fast"]),
        Backend("PIL",     "PIL",     weight=80, tags=["standard"], adapter="image_pillow"),
        Backend("skimage", "skimage", weight=70, tags=["scientific"]),
    ],

    # ── MACHINE LEARNING ───────────────────────────────────────────────────
    "ml": [
        Backend("torch",       "torch",       weight=95, gpu_preferred=True, tags=["deep_learning"]),
        Backend("xgboost",     "xgboost",     weight=85, tags=["gradient_boost", "fast"]),
        Backend("lightgbm",    "lightgbm",    weight=85, tags=["gradient_boost", "fast"]),
        Backend("sklearn",     "sklearn",     weight=70, tags=["classical", "standard"]),
        Backend("statsmodels", "statsmodels", weight=60, tags=["statistics"]),
    ],

    # ── NLP ────────────────────────────────────────────────────────────────
    "nlp": [
        Backend("transformers", "transformers", weight=95, gpu_preferred=True, tags=["llm", "bert"]),
        Backend("spacy",        "spacy",        weight=80, tags=["fast", "ner"]),
        Backend("nltk",         "nltk",         weight=60, tags=["classical"]),
    ],

    # ── VISUALIZATION ──────────────────────────────────────────────────────
    "viz": [
        Backend("plotly",     "plotly",     weight=90, tags=["interactive"]),
        Backend("altair",     "altair",     weight=80, tags=["declarative"]),
        Backend("seaborn",    "seaborn",    weight=75, tags=["statistical"]),
        Backend("matplotlib", "matplotlib", weight=70, tags=["standard"]),
    ],

    # ── STATISTICS ─────────────────────────────────────────────────────────
    "stats": [
        Backend("statsmodels", "statsmodels", weight=90, tags=["econometrics"]),
        Backend("scipy",       "scipy",       weight=80, tags=["scientific"]),
        Backend("sklearn",     "sklearn",     weight=70, tags=["ml_stats"]),
    ],

    # ── HTTP / NETWORKING ──────────────────────────────────────────────────
    "http": [
        Backend("httpx",    "httpx",    weight=90, tags=["async", "modern"]),
        Backend("requests", "requests", weight=80, tags=["standard", "sync"]),
        Backend("urllib3",  "urllib3",  weight=60, tags=["low_level"]),
    ],

    # ── JSON / SERIALIZATION ───────────────────────────────────────────────
    "json": [
        Backend("orjson",   "orjson",   weight=95, tags=["fast"]),
        Backend("ujson",    "ujson",    weight=85, tags=["fast"]),
        Backend("json",     "json",     weight=70, tags=["stdlib"]),
    ],
}


class Registry:
    """Query interface over REGISTRY."""

    @staticmethod
    def backends_for(domain: str) -> list[Backend]:
        """Return all registered backends for a domain (unsorted)."""
        return REGISTRY.get(domain, [])

    @staticmethod
    def available_backends(domain: str) -> list[str]:
        """Return names of backends that are currently importable."""
        result = []
        for b in REGISTRY.get(domain, []):
            if importlib.util.find_spec(b.import_name) is not None:
                result.append(b.name)
        return result

    @staticmethod
    def best_backend(
        domain: str,
        cuda: bool = False,
        mps: bool = False,
        prefer_gpu: bool = True,
        force: Optional[str] = None,
    ) -> Optional[Backend]:
        """
        Select the highest-weight available backend for a domain.

        Args:
            domain:     e.g. 'math', 'dataframe'
            cuda:       whether CUDA is available
            mps:        whether Apple MPS is available
            prefer_gpu: boost GPU backends when hardware exists
            force:      override selection with a specific backend name

        Returns:
            The winning Backend, or None if nothing is installed.
        """
        candidates = REGISTRY.get(domain, [])
        if not candidates:
            logger.warning("No backends registered for domain '%s'", domain)
            return None

        scored = []
        for b in candidates:
            # Hard exclusions
            if b.requires_cuda and not cuda:
                continue
            if b.requires_mps and not mps:
                continue

            # Check importable
            if importlib.util.find_spec(b.import_name) is None:
                continue

            # Force override
            if force and b.name == force:
                return b

            # Effective weight
            effective = b.weight
            if b.gpu_preferred and (cuda or mps) and prefer_gpu:
                effective += 20  # Boost GPU backends on GPU machines

            scored.append((effective, b))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        winner = scored[0][1]
        logger.info("domain='%s' → backend='%s' (score=%d)", domain, winner.name, scored[0][0])
        return winner

    @staticmethod
    def register(domain: str, backend: Backend):
        """Register a new backend at runtime (plugin/extension support)."""
        if domain not in REGISTRY:
            REGISTRY[domain] = []
        REGISTRY[domain].append(backend)
        logger.info("Registered backend '%s' for domain '%s'", backend.name, domain)
