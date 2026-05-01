"""
shaaha.router
=============
The "Brain" of Shaaha.

Given a domain, the Router consults the Registry and Environment
to pick the optimal backend. Results are cached so routing happens
only once per domain per session.
"""

from __future__ import annotations

import logging
import importlib
from typing import Any, Optional

from shaaha.registry import Registry, Backend
from shaaha.environment import Environment

logger = logging.getLogger("shaaha.router")

# Lazy environment reference — populated on first use
_env: Optional[Environment] = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment.probe()
    return _env


class _RouterMeta(type):
    """Singleton metaclass with per-domain cache."""

    _cache: dict[str, Any] = {}
    _config: dict = {
        "prefer_gpu": True,
        "auto_install": False,
        "force_backend": {},
    }

    def configure(cls, **kwargs):
        cls._config.update(kwargs)
        cls._cache.clear()  # Invalidate cache when config changes
        logger.debug("Router reconfigured: %s", cls._config)

    def selected_backends(cls) -> dict[str, str]:
        return {domain: mod.__name__ for domain, mod in cls._cache.items()}


class Router(metaclass=_RouterMeta):
    """
    Resolves and imports the best backend module for a given domain.
    All resolved modules are cached for zero-overhead repeat access.
    """

    @classmethod
    def resolve(cls, domain: str) -> Any:
        """
        Return the best importable backend module for `domain`.

        Raises:
            ImportError: if no backend is available and auto_install is False.
        """
        if domain in cls._cache:
            return cls._cache[domain]

        env = _get_env()
        force = cls._config["force_backend"].get(domain)

        backend: Optional[Backend] = Registry.best_backend(
            domain=domain,
            cuda=env.cuda_available,
            mps=env.mps_available,
            prefer_gpu=cls._config["prefer_gpu"],
            force=force,
        )

        if backend is None:
            if cls._config["auto_install"]:
                backend = cls._try_auto_install(domain)

            if backend is None:
                available = Registry.available_backends(domain)
                raise ImportError(
                    f"[Shaaha] No backend available for domain '{domain}'.\n"
                    f"  Install one of: {[b.name for b in Registry.backends_for(domain)]}\n"
                    f"  Currently installed: {available or 'none'}\n"
                    f"  Tip: shaaha.configure(auto_install=True) to auto-install."
                )

        # If the backend has a wrapper/adapter, load that instead
        if backend.adapter:
            mod = cls._load_adapter(backend.adapter, backend)
        else:
            mod = importlib.import_module(backend.import_name)

        cls._cache[domain] = mod
        logger.info("Resolved: shaaha.%s → %s", domain, backend.import_name)
        return mod

    @classmethod
    def _load_adapter(cls, adapter_name: str, backend: Backend) -> Any:
        """Load a Shaaha wrapper that normalises a backend's API."""
        try:
            adapter_mod = importlib.import_module(f"shaaha.wrappers.{adapter_name}")
            return adapter_mod
        except ImportError:
            logger.warning("Adapter '%s' not found, falling back to raw backend", adapter_name)
            return importlib.import_module(backend.import_name)

    @classmethod
    def _try_auto_install(cls, domain: str) -> Optional[Backend]:
        """
        Attempt to pip-install the highest-weight backend for a domain.
        Only runs when auto_install=True.
        """
        from shaaha.installer import Installer

        candidates = Registry.backends_for(domain)
        env = _get_env()

        for b in sorted(candidates, key=lambda x: x.weight, reverse=True):
            if b.requires_cuda and not env.cuda_available:
                continue
            success = Installer.install(b.name)
            if success:
                return b
        return None
