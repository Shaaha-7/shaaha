"""
shaaha.importer
===============
Implements PEP 302 / PEP 451 compliant Finder and Loader.

When Python encounters `import shaaha.math`, it walks sys.meta_path
looking for a Finder that claims the module. ShaahafFinder intercepts
any `shaaha.<domain>` import and returns a dynamically-constructed
proxy module — no physical file needed.
"""

from __future__ import annotations

import sys
import types
import logging
import importlib.abc
import importlib.machinery
from typing import Optional

logger = logging.getLogger("shaaha.importer")

_SHAAHA_PACKAGE = "shaaha"


class ShaahafFinder(importlib.abc.MetaPathFinder):
    """
    Intercepts imports of the form `shaaha.<domain>`.
    Registered in sys.meta_path by shaaha.__init__.
    """

    def find_spec(
        self,
        fullname: str,
        path: Optional[list],
        target=None,
    ) -> Optional[importlib.machinery.ModuleSpec]:

        # Only intercept shaaha.* sub-modules (not shaaha itself)
        if not fullname.startswith(_SHAAHA_PACKAGE + "."):
            return None

        parts = fullname.split(".")
        if len(parts) < 2:
            return None

        domain = parts[1]  # e.g. 'math', 'dataframe', 'image'

        # Skip internal shaaha sub-packages (importer, router, etc.)
        _internals = {
            "importer", "router", "registry",
            "environment", "proxy", "installer", "wrappers",
            "brain", "healer", "agent", "rewriter", "explainer",
            "dashboard", "plugins", "collab", "safety", "_llm", "cli",
            }
        if domain in _internals:
            return None

        logger.debug("ShaahafFinder intercepted: %s → domain=%s", fullname, domain)

        loader = ShaahaaLoader(fullname, domain)
        spec = importlib.machinery.ModuleSpec(
            fullname,
            loader,
            is_package=False,
        )
        return spec


class ShaahaaLoader(importlib.abc.Loader):
    """
    Builds and returns a ProxyModule for the requested domain.
    No third-party library is imported here — all imports are deferred
    to the moment a user calls an attribute on the proxy.
    """

    def __init__(self, fullname: str, domain: str):
        self.fullname = fullname
        self.domain = domain

    # PEP 451
    def create_module(self, spec):
        return None  # Use default semantics

    def exec_module(self, module):
        from shaaha.proxy import ProxyModule
        from shaaha.router import Router
        from shaaha.healer import get_healer

        # Inject proxy behaviour into the module namespace
        proxy = ProxyModule(self.domain, Router, get_healer())
        module.__class__ = proxy.__class__
        module.__dict__.update(proxy.__dict__)
        module.__loader__ = self
        module.__spec__ = None  # Prevent re-entry
        logger.info("Loaded proxy module for domain '%s'", self.domain)

    # Legacy PEP 302 fallback
    def load_module(self, fullname: str):
        if fullname in sys.modules:
            return sys.modules[fullname]

        from shaaha.proxy import ProxyModule
        from shaaha.router import Router
        from shaaha.healer import get_healer

        mod = types.ModuleType(fullname)
        mod.__loader__ = self
        mod.__package__ = _SHAAHA_PACKAGE
        mod.__spec__ = None

        proxy = ProxyModule(self.domain, Router, get_healer())
        mod.__class__ = proxy.__class__
        mod.__dict__.update(proxy.__dict__)

        sys.modules[fullname] = mod
        return mod
