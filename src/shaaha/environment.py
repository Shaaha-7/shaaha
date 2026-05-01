"""
shaaha.environment
==================
Probes the runtime environment ONCE at startup.
All checks are intentionally lightweight — no heavy imports.
"""

from __future__ import annotations

import os
import sys
import platform
import logging
import importlib.util
from dataclasses import dataclass, asdict, field
from typing import Optional

logger = logging.getLogger("shaaha.environment")


def _is_importable(name: str) -> bool:
    """Return True if `name` can be imported without actually importing it."""
    return importlib.util.find_spec(name) is not None


@dataclass
class Environment:
    python_version: str = ""
    os_name: str = ""
    cpu_cores: int = 1
    cuda_available: bool = False
    cuda_device: Optional[str] = None
    rocm_available: bool = False   # AMD GPU
    mps_available: bool = False    # Apple Silicon
    installed_packages: dict = field(default_factory=dict)

    # Domain → preferred backend resolved during probe
    _resolved: dict = field(default_factory=dict, repr=False)

    @classmethod
    def probe(cls) -> "Environment":
        env = cls()
        env.python_version = platform.python_version()
        env.os_name = platform.system()

        # CPU
        try:
            import os as _os
            env.cpu_cores = _os.cpu_count() or 1
        except Exception:
            pass

        # CUDA via torch (lightweight check — spec only)
        if _is_importable("torch"):
            try:
                import torch
                if torch.cuda.is_available():
                    env.cuda_available = True
                    env.cuda_device = torch.cuda.get_device_name(0)
            except Exception:
                pass
        elif _is_importable("cupy"):
            try:
                import cupy
                env.cuda_available = cupy.is_available()
                if env.cuda_available:
                    env.cuda_device = "CuPy GPU"
            except Exception:
                pass

        # Apple MPS
        if _is_importable("torch"):
            try:
                import torch
                env.mps_available = torch.backends.mps.is_available()
            except Exception:
                pass

        # Probe which key libraries are installed (spec-only, no import)
        _candidates = [
            # dataframe
            "pandas", "polars", "modin", "dask",
            # math / array
            "numpy", "cupy", "jax", "torch",
            # image
            "PIL", "cv2", "skimage",
            # ml
            "sklearn", "torch", "xgboost", "lightgbm",
            # nlp
            "transformers", "spacy", "nltk",
            # viz
            "matplotlib", "plotly", "altair", "seaborn",
            # stats
            "statsmodels", "scipy",
        ]
        env.installed_packages = {pkg: _is_importable(pkg) for pkg in _candidates}

        logger.debug("Environment probed: %s", env)
        return env

    def has(self, package: str) -> bool:
        return self.installed_packages.get(package, _is_importable(package))

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_resolved", None)
        return d
