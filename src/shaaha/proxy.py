"""
shaaha.proxy
============
ProxyModule — transparent lazy proxy over any backend module.

BUG FIX v2.0: sklearn and other backends expose classes at submodule level
(sklearn.linear_model.LinearRegression). The proxy now walks all submodules
to build a flat attribute map so shaaha.ml.LinearRegression() works directly.
"""
from __future__ import annotations
import types
import logging
import importlib
from typing import Any

logger = logging.getLogger("shaaha.proxy")


def _build_flat_map(module) -> dict:
    """
    Build a flat {name: obj} map by walking all public submodules.
    This makes sklearn's LinearRegression accessible as shaaha.ml.LinearRegression.
    """
    flat = {}
    # First pass: direct attributes
    for name in dir(module):
        if not name.startswith("_"):
            try:
                flat[name] = getattr(module, name)
            except Exception:
                pass

    # Second pass: walk submodules (e.g. sklearn.linear_model, sklearn.ensemble)
    pkg = getattr(module, "__package__", None) or getattr(module, "__name__", None)
    if pkg:
        import pkgutil
        try:
            for importer, modname, ispkg in pkgutil.walk_packages(
                path=getattr(module, "__path__", None),
                prefix=pkg + ".",
                onerror=lambda x: None,
            ):
                # Only one level deep to stay fast
                if modname.count(".") > 1:
                    continue
                try:
                    sub = importlib.import_module(modname)
                    for attr in dir(sub):
                        if not attr.startswith("_") and attr not in flat:
                            try:
                                flat[attr] = getattr(sub, attr)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass
    return flat


class ProxyModule(types.ModuleType):
    """
    Lazy proxy module — resolves and delegates to real backend on first use.
    Supports flat attribute access across all submodules (fixes sklearn bug).
    """

    def __init__(self, domain: str, router_cls, healer_cls=None):
        super().__init__(f"shaaha.{domain}")
        object.__setattr__(self, "_shaaha_domain", domain)
        object.__setattr__(self, "_shaaha_router", router_cls)
        object.__setattr__(self, "_shaaha_healer", healer_cls)
        object.__setattr__(self, "_shaaha_backend", None)
        object.__setattr__(self, "_shaaha_flat_map", None)
        self.__doc__ = (
            f"Shaaha proxy for domain '{domain}'.\n"
            f"Auto-routes to best available backend.\n"
            f"Use shaaha.available_backends('{domain}') to see options."
        )

    def _resolve(self) -> Any:
        backend = object.__getattribute__(self, "_shaaha_backend")
        if backend is None:
            domain = object.__getattribute__(self, "_shaaha_domain")
            router = object.__getattribute__(self, "_shaaha_router")
            backend = router.resolve(domain)
            object.__setattr__(self, "_shaaha_backend", backend)
            # Build flat map for submodule walking
            flat = _build_flat_map(backend)
            object.__setattr__(self, "_shaaha_flat_map", flat)
            logger.debug("ProxyModule '%s' resolved → %s", domain, backend)
        return backend

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)

        self._resolve()
        flat_map = object.__getattribute__(self, "_shaaha_flat_map")
        backend  = object.__getattribute__(self, "_shaaha_backend")

        # Try flat map first (catches sklearn submodule classes)
        if flat_map and name in flat_map:
            return flat_map[name]

        # Try direct attribute
        try:
            return getattr(backend, name)
        except AttributeError:
            pass

        # Self-healer fallback
        healer = object.__getattribute__(self, "_shaaha_healer")
        if healer:
            domain = object.__getattribute__(self, "_shaaha_domain")
            new_backend = healer.try_fallback(domain, name)
            if new_backend is not None:
                object.__setattr__(self, "_shaaha_backend", new_backend)
                flat = _build_flat_map(new_backend)
                object.__setattr__(self, "_shaaha_flat_map", flat)
                if name in flat:
                    return flat[name]
                try:
                    return getattr(new_backend, name)
                except AttributeError:
                    pass

        domain = object.__getattribute__(self, "_shaaha_domain")
        bname = getattr(backend, "__name__", str(backend))
        raise AttributeError(
            f"[Shaaha] Backend for '{domain}' has no attribute '{name}'.\n"
            f"  Backend: {bname}\n"
            f"  Tip: shaaha.available_backends('{domain}') to see alternatives.\n"
            f"  Tip: shaaha.configure(force_backend={{'{domain}': 'other_lib'}}) to switch."
        )

    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __repr__(self) -> str:
        domain = object.__getattribute__(self, "_shaaha_domain")
        backend = object.__getattribute__(self, "_shaaha_backend")
        if backend:
            return f"<ShaahProxy domain='{domain}' backend='{getattr(backend,'__name__',backend)}'>"
        return f"<ShaahProxy domain='{domain}' backend=not-yet-resolved>"

    def __dir__(self):
        try:
            self._resolve()
            flat = object.__getattribute__(self, "_shaaha_flat_map") or {}
            return list(flat.keys())
        except ImportError:
            return super().__dir__()
