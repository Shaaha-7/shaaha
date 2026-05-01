"""
Shaaha - Intelligent Meta-Dispatcher for Python
================================================
Author: Shaaha
License: MIT

Shaaha abstracts all Python libraries behind a single unified interface.
It automatically selects the best backend based on your hardware,
data scale, and installed dependencies — zero config required.

Usage:
    import shaaha
    df = shaaha.dataframe.read_csv("data.csv")   # auto picks pandas/polars
    arr = shaaha.math.array([1, 2, 3])            # auto picks numpy/cupy/jax
    img = shaaha.image.open("photo.jpg")          # auto picks pillow/opencv
"""

import sys
import logging
from shaaha.importer import ShaahafFinder
from shaaha.environment import Environment

__version__ = "1.0.0"
__author__ = "Shaaha"
__license__ = "MIT"
__all__ = ["__version__", "configure", "status", "available_backends"]

# Configure logging
logging.getLogger("shaaha").addHandler(logging.NullHandler())

# --- Register the Meta-Path Hook ---
_finder = ShaahafFinder()
if not any(isinstance(f, ShaahafFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _finder)

# Probe environment once at import time (lightweight)
_env = Environment.probe()


def configure(
    prefer_gpu: bool = True,
    auto_install: bool = False,
    log_level: str = "WARNING",
    force_backend: dict = None,
):
    """
    Configure Shaaha's global routing behaviour.

    Args:
        prefer_gpu:    Prefer GPU-accelerated backends when available.
        auto_install:  Offer to pip-install missing best backends.
        log_level:     Logging verbosity ('DEBUG', 'INFO', 'WARNING').
        force_backend: Override routing for a domain, e.g. {'math': 'numpy'}.

    Example:
        shaaha.configure(prefer_gpu=False, auto_install=True)
    """
    from shaaha.router import Router

    logging.getLogger("shaaha").setLevel(getattr(logging, log_level.upper(), logging.WARNING))
    Router.configure(
        prefer_gpu=prefer_gpu,
        auto_install=auto_install,
        force_backend=force_backend or {},
    )


def status() -> dict:
    """
    Return a summary of the current environment and selected backends.

    Returns:
        dict with keys: python_version, cuda_available, backends_selected, env
    """
    from shaaha.router import Router

    return {
        "version": __version__,
        "python": _env.python_version,
        "cuda_available": _env.cuda_available,
        "cuda_device": _env.cuda_device,
        "cpu_cores": _env.cpu_cores,
        "selected_backends": Router.selected_backends(),
        "environment": _env.to_dict(),
    }


def available_backends(domain: str) -> list:
    """
    List all installed backends for a given Shaaha domain.

    Args:
        domain: e.g. 'math', 'dataframe', 'image', 'ml'

    Returns:
        List of backend names that are currently importable.

    Example:
        shaaha.available_backends('dataframe')  # ['polars', 'pandas']
    """
    from shaaha.registry import Registry

    return Registry.available_backends(domain)
