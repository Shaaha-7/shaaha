"""
shaaha.plugins — Layer 8: The Plugin System
============================================
Allows anyone to register custom backends at runtime or permanently.

shaaha.register_backend(
    domain="dataframe",
    name="my_fast_lib",
    priority=95,
    import_path="my_fast_lib"
)

shaaha.list_backends()
"""
from __future__ import annotations

import json
import logging
import importlib.util
from pathlib import Path
from typing import Optional

logger = logging.getLogger("shaaha.plugins")

_PLUGINS_FILE = Path.home() / ".shaaha" / "plugins.json"


class PluginRegistry:
    """Manages user-registered custom backends."""

    _instance: Optional["PluginRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = cls._instance._load()
        return cls._instance

    def _load(self) -> dict:
        try:
            if _PLUGINS_FILE.exists():
                return json.loads(_PLUGINS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Plugins: load failed: %s", e)
        return {}

    def _save(self):
        try:
            _PLUGINS_FILE.parent.mkdir(parents=True, exist_ok=True)
            _PLUGINS_FILE.write_text(json.dumps(self._plugins, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Plugins: save failed: %s", e)

    def register(self, domain: str, name: str, import_path: str,
                 priority: int = 80, tags: Optional[list] = None,
                 gpu_preferred: bool = False):
        """
        Register a custom backend permanently.

        Args:
            domain:       shaaha domain (e.g. 'dataframe', 'math')
            name:         display name (e.g. 'my_custom_lib')
            import_path:  Python import path (e.g. 'my_custom_lib.core')
            priority:     weight 0-100 (higher = preferred)
            tags:         optional list of capability tags
            gpu_preferred: boost this backend when GPU is available

        Example:
            shaaha.register_backend('dataframe', 'vaex', 'vaex', priority=88)
        """
        from shaaha.registry import Registry, Backend

        # Validate import_path is importable
        if importlib.util.find_spec(import_path.split(".")[0]) is None:
            print(f"⚠️  [Shaaha] '{import_path}' is not currently importable. "
                  f"Install it first: pip install {name}")

        backend = Backend(
            name=name,
            import_name=import_path,
            weight=priority,
            gpu_preferred=gpu_preferred,
            tags=tags or ["custom", "plugin"],
        )

        # Register in live registry
        Registry.register(domain, backend)

        # Persist
        key = f"{domain}::{name}"
        self._plugins[key] = {
            "domain": domain, "name": name,
            "import_path": import_path, "priority": priority,
            "tags": tags or [], "gpu_preferred": gpu_preferred,
        }
        self._save()

        print(f"✅ [Shaaha] Registered '{name}' as backend for '{domain}' "
              f"(priority={priority})")
        logger.info("Plugin registered: %s → %s", domain, name)

    def unregister(self, domain: str, name: str):
        """Remove a registered plugin."""
        key = f"{domain}::{name}"
        if key in self._plugins:
            del self._plugins[key]
            self._save()
            print(f"🗑️  [Shaaha] Unregistered '{name}' from '{domain}'")
        else:
            print(f"[Shaaha] Plugin '{name}' not found in domain '{domain}'")

    def load_all(self):
        """Load all persisted plugins into the live registry (called at startup)."""
        from shaaha.registry import Registry, Backend
        for key, p in self._plugins.items():
            try:
                Registry.register(p["domain"], Backend(
                    name=p["name"], import_name=p["import_path"],
                    weight=p["priority"], gpu_preferred=p.get("gpu_preferred", False),
                    tags=p.get("tags", ["custom"]),
                ))
            except Exception as e:
                logger.warning("Failed to load plugin %s: %s", key, e)

    def list_all(self) -> dict:
        """Return all registered plugins."""
        return dict(self._plugins)


def register_backend(domain: str, name: str, import_path: str,
                     priority: int = 80, tags: Optional[list] = None,
                     gpu_preferred: bool = False):
    """
    Public API — register a custom backend.

    Example:
        import shaaha
        shaaha.register_backend('dataframe', 'vaex', 'vaex', priority=88)
    """
    PluginRegistry().register(domain, name, import_path, priority, tags, gpu_preferred)


def list_backends(domain: Optional[str] = None):
    """
    Public API — list all available and custom backends.

    Example:
        import shaaha
        shaaha.list_backends()
        shaaha.list_backends('math')
    """
    from shaaha.registry import REGISTRY, Registry
    import importlib.util

    domains = [domain] if domain else list(REGISTRY.keys())

    print("\n📦 [Shaaha] Available Backends\n")
    print(f"  {'Domain':<14} {'Backend':<16} {'Weight':>6}  {'Installed':>9}  Tags")
    print("  " + "─" * 65)

    for dom in domains:
        backends = REGISTRY.get(dom, [])
        for b in sorted(backends, key=lambda x: x.weight, reverse=True):
            installed = "✅ yes" if importlib.util.find_spec(b.import_name) else "❌ no"
            tags_str  = ", ".join(b.tags[:3]) if b.tags else ""
            marker    = " ★" if "custom" in b.tags else ""
            print(f"  {dom:<14} {b.name:<16} {b.weight:>6}  {installed:>9}  {tags_str}{marker}")
        if backends:
            print()

    # Custom plugins
    custom = PluginRegistry().list_all()
    if custom:
        print(f"  ★ = custom plugin  |  {len(custom)} plugin(s) registered\n")
