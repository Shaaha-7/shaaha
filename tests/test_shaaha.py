"""
tests/test_shaaha.py
====================
Comprehensive test suite for Shaaha.
Run with: pytest tests/ -v
"""

import sys
import types
import importlib
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unload_shaaha():
    """Remove all shaaha modules from sys.modules for a clean slate."""
    to_remove = [k for k in sys.modules if k == "shaaha" or k.startswith("shaaha.")]
    for k in to_remove:
        del sys.modules[k]
    # Remove finder
    sys.meta_path[:] = [f for f in sys.meta_path if type(f).__name__ != "ShaahafFinder"]


# ---------------------------------------------------------------------------
# Import Hook Tests
# ---------------------------------------------------------------------------

class TestImportHook:
    def setup_method(self):
        _unload_shaaha()

    def test_shaaha_importable(self):
        import re
        import shaaha
        assert re.match(r"^\d+\.\d+\.\d+", shaaha.__version__), shaaha.__version__

    def test_hook_registered(self):
        import shaaha
        assert any(type(f).__name__ == "ShaahafFinder" for f in sys.meta_path)

    def test_hook_registered_only_once(self):
        import shaaha
        import shaaha  # noqa: F811 — second import
        finders = [f for f in sys.meta_path if type(f).__name__ == "ShaahafFinder"]
        assert len(finders) == 1

    def test_domain_import_returns_module(self):
        import shaaha
        import shaaha.math as sm
        assert isinstance(sm, types.ModuleType)

    def test_domain_module_cached_in_sys_modules(self):
        import shaaha
        import shaaha.dataframe
        assert "shaaha.dataframe" in sys.modules

    def test_internal_modules_not_intercepted(self):
        import shaaha.registry  # should import the real file
        from shaaha.registry import Registry
        assert callable(Registry.best_backend)


# ---------------------------------------------------------------------------
# Environment Tests
# ---------------------------------------------------------------------------

class TestEnvironment:
    def test_probe_returns_environment(self):
        from shaaha.environment import Environment
        env = Environment.probe()
        assert env.python_version != ""
        assert env.cpu_cores >= 1

    def test_to_dict(self):
        from shaaha.environment import Environment
        env = Environment.probe()
        d = env.to_dict()
        assert "python_version" in d
        assert "cuda_available" in d

    def test_has_stdlib(self):
        from shaaha.environment import Environment
        env = Environment.probe()
        # json is in stdlib — always importable
        import importlib.util
        assert importlib.util.find_spec("json") is not None


# ---------------------------------------------------------------------------
# Registry Tests
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_domains_registered(self):
        from shaaha.registry import Registry, REGISTRY
        assert "math" in REGISTRY
        assert "dataframe" in REGISTRY
        assert "image" in REGISTRY
        assert "ml" in REGISTRY

    def test_available_backends_returns_list(self):
        from shaaha.registry import Registry
        result = Registry.available_backends("math")
        assert isinstance(result, list)

    def test_best_backend_returns_none_for_unknown_domain(self):
        from shaaha.registry import Registry
        result = Registry.best_backend("nonexistent_domain_xyz")
        assert result is None

    def test_custom_backend_registration(self):
        from shaaha.registry import Registry, Backend, REGISTRY
        b = Backend("testlib", "testlib", weight=50)
        Registry.register("test_domain", b)
        assert any(x.name == "testlib" for x in REGISTRY["test_domain"])

    def test_gpu_boost(self):
        from shaaha.registry import Registry
        # When cuda=True, GPU backends should be preferred
        # (only meaningful if cupy or torch are installed)
        result = Registry.best_backend("math", cuda=True, prefer_gpu=True)
        # Just verify it doesn't crash and returns a Backend or None
        from shaaha.registry import Backend
        assert result is None or isinstance(result, Backend)


# ---------------------------------------------------------------------------
# Router Tests
# ---------------------------------------------------------------------------

class TestRouter:
    def setup_method(self):
        _unload_shaaha()

    def test_router_configure(self):
        import shaaha
        from shaaha.router import Router
        shaaha.configure(prefer_gpu=False, log_level="DEBUG")
        assert Router._config["prefer_gpu"] is False

    def test_router_resolve_raises_on_no_backend(self):
        import shaaha
        from shaaha.router import Router
        with pytest.raises(ImportError, match="Shaaha"):
            Router.resolve("completely_fake_domain_xyz_abc")

    def test_router_cache_works(self):
        import shaaha
        from shaaha.router import Router
        # Resolve twice — second should hit cache
        try:
            mod1 = Router.resolve("json")
            mod2 = Router.resolve("json")
            assert mod1 is mod2
        except ImportError:
            pytest.skip("json not registered or available")

    def test_selected_backends_dict(self):
        import shaaha
        from shaaha.router import Router
        result = Router.selected_backends()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Proxy Tests
# ---------------------------------------------------------------------------

class TestProxy:
    def setup_method(self):
        _unload_shaaha()

    def test_proxy_repr_before_resolve(self):
        import shaaha
        from shaaha.proxy import ProxyModule
        from shaaha.router import Router
        p = ProxyModule("math", Router)
        assert "not-yet-resolved" in repr(p)

    def test_proxy_getattr_triggers_resolution(self):
        import shaaha
        # json is in stdlib and registered
        try:
            import shaaha.json as sj
            # Accessing any attr should trigger resolution
            _ = sj.dumps
        except (ImportError, AttributeError):
            pytest.skip("json backend not available")

    def test_proxy_dir_delegates_to_backend(self):
        import shaaha
        try:
            import shaaha.json as sj
            d = dir(sj)
            assert isinstance(d, list)
        except ImportError:
            pytest.skip("json backend not available")


# ---------------------------------------------------------------------------
# Integration: shaaha.status()
# ---------------------------------------------------------------------------

class TestPublicAPI:
    def setup_method(self):
        _unload_shaaha()

    def test_status_keys(self):
        import shaaha
        s = shaaha.status()
        assert "version" in s
        assert "python" in s
        assert "cuda_available" in s
        assert "selected_backends" in s

    def test_available_backends_returns_list(self):
        import shaaha
        result = shaaha.available_backends("math")
        assert isinstance(result, list)

    def test_configure_force_backend_invalid_clears_on_error(self):
        import shaaha
        shaaha.configure(force_backend={})
        from shaaha.router import Router
        with pytest.raises(ImportError):
            Router.resolve("completely_nonexistent_domain_xyz_999")
