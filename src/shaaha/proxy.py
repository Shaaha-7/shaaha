"""
shaaha.proxy
============
ProxyModule — the object the user interacts with after `import shaaha.math`.

Every attribute access (shaaha.math.array, shaaha.dataframe.read_csv, ...)
triggers lazy backend resolution ONLY at the moment of first call.
The real backend module is cached after the first resolution.
"""

from __future__ import annotations

import types
import logging
from typing import Any

logger = logging.getLogger("shaaha.proxy")


class ProxyModule(types.ModuleType):
    """
    A module-like object that forwards all attribute access to the
    resolved backend, resolving lazily on first use.

    Features:
    - Zero import cost until first attribute access.
    - Full __dir__ and __repr__ for IDE autocomplete friendliness.
    - Transparent: behaves exactly like the underlying backend module.
    """

    def __init__(self, domain: str, router_cls):
        super().__init__(f"shaaha.{domain}")
        # Store in __dict__ directly to avoid triggering __getattr__
        object.__setattr__(self, "_shaaha_domain", domain)
        object.__setattr__(self, "_shaaha_router", router_cls)
        object.__setattr__(self, "_shaaha_backend", None)
        self.__doc__ = (
            f"Shaaha proxy for domain '{domain}'.\n"
            f"Automatically routes to the best available backend.\n"
            f"Use `shaaha.available_backends('{domain}')` to see options."
        )

    def _resolve(self) -> Any:
        backend = object.__getattribute__(self, "_shaaha_backend")
        if backend is None:
            domain = object.__getattribute__(self, "_shaaha_domain")
            router = object.__getattribute__(self, "_shaaha_router")
            backend = router.resolve(domain)
            object.__setattr__(self, "_shaaha_backend", backend)
            logger.debug("ProxyModule '%s' resolved to %s", domain, backend)
        return backend

    def __getattr__(self, name: str) -> Any:
        # Skip dunder lookups to avoid recursion
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        backend = self._resolve()
        try:
            return getattr(backend, name)
        except AttributeError:
            domain = object.__getattribute__(self, "_shaaha_domain")
            raise AttributeError(
                f"[Shaaha] Backend for '{domain}' has no attribute '{name}'.\n"
                f"  Backend: {backend.__name__ if hasattr(backend, '__name__') else backend}\n"
                f"  Tip: call `import shaaha; shaaha.available_backends('{domain}')` "
                f"to see alternatives."
            ) from None

    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __repr__(self) -> str:
        domain = object.__getattribute__(self, "_shaaha_domain")
        backend = object.__getattribute__(self, "_shaaha_backend")
        if backend:
            bname = getattr(backend, "__name__", str(backend))
            return f"<ShaahProxy domain='{domain}' backend='{bname}'>"
        return f"<ShaahProxy domain='{domain}' backend=not-yet-resolved>"

    def __dir__(self):
        try:
            backend = self._resolve()
            return dir(backend)
        except ImportError:
            return super().__dir__()
