"""
tests/conftest.py
==================
Brain and PluginRegistry persist to ~/.shaaha/*.json by default. Without
this fixture the test suite silently writes fake data into the real
user's home directory - confirmed by hand: running the suite left
"testplugin"/"vaex" entries in the *actual* ~/.shaaha/plugins.json and
fabricated timing data in profile.json, visible from a plain interactive
`shaaha.diagnose()` call outside of any test.

Patching Path.home() itself (rather than shaaha.brain._PROFILE_DIR /
shaaha.plugins._PLUGINS_FILE directly) matters here: most test files call
a `_clean()` helper that deletes `shaaha` and `shaaha.*` from
sys.modules so the import hook can be re-tested from scratch. That
re-executes brain.py/plugins.py on the next import, which would silently
recompute `Path.home() / ".shaaha"` back to the real path and discard a
monkeypatch on the old module object. Patching the classmethod both
modules call to build that path survives the re-import.
"""
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def _shaaha_home_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("shaaha_home")


@pytest.fixture(autouse=True)
def isolate_shaaha_home(_shaaha_home_dir, monkeypatch):
    """Redirect Path.home() for the duration of every test, and reset
    Brain/PluginRegistry singletons that may already be holding data
    loaded from the real path."""
    monkeypatch.setattr(Path, "home", lambda: _shaaha_home_dir)

    import shaaha.brain as brain_mod
    import shaaha.plugins as plugins_mod
    brain_mod.Brain._instance = None
    plugins_mod.PluginRegistry._instance = None

    yield

    brain_mod.Brain._instance = None
    plugins_mod.PluginRegistry._instance = None
