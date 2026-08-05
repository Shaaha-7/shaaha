"""
tests/test_shaaha_v2.py
=======================
Full test suite for Shaaha v2.0 — all 10 layers.
Run: pytest tests/ -v
"""
import sys, types, json, importlib, pytest
from pathlib import Path

# ── helpers ───────────────────────────────────────────────────────────────────
def _clean():
    for k in list(sys.modules):
        if k == "shaaha" or k.startswith("shaaha."):
            del sys.modules[k]
    sys.meta_path[:] = [f for f in sys.meta_path if type(f).__name__ != "ShaahafFinder"]

# ═══════════════════════════════════════════════════════════════════════
# BUG FIX — sklearn proxy
# ═══════════════════════════════════════════════════════════════════════
class TestSklearnProxyFix:
    def setup_method(self): _clean()

    def test_linear_regression_accessible(self):
        import shaaha
        shaaha.configure(force_backend={"ml": "sklearn"})
        import shaaha.ml as ml
        LR = ml.LinearRegression
        assert LR is not None
        model = LR()
        assert hasattr(model, "fit")

    def test_train_test_split_accessible(self):
        import shaaha
        shaaha.configure(force_backend={"ml": "sklearn"})
        import shaaha.ml as ml
        tts = ml.train_test_split
        assert callable(tts)

    def test_numpy_array_accessible(self):
        import shaaha
        import shaaha.math as sm
        arr = sm.array([1, 2, 3])
        assert list(arr) == [1, 2, 3]

# ═══════════════════════════════════════════════════════════════════════
# LAYER 4 — Adaptive Brain
# ═══════════════════════════════════════════════════════════════════════
class TestBrain:
    def test_brain_singleton(self):
        from shaaha.brain import Brain
        a, b = Brain(), Brain()
        assert a is b

    def test_record_and_retrieve(self):
        from shaaha.brain import Brain
        b = Brain()
        b.record("math", "numpy", 12.5)
        ops = b._data["operations"]
        assert "math::numpy" in ops
        assert 12.5 in ops["math::numpy"]["timings"]

    def test_confidence_zero_start(self):
        from shaaha.brain import Brain
        b = Brain()
        b.reset()
        assert b.confidence() == 0.0

    def test_confidence_grows(self):
        from shaaha.brain import Brain
        b = Brain()
        b.reset()
        for i in range(10):
            b.record("math", "numpy", float(i + 1))
        assert b.confidence() > 0.0

    def test_summary_returns_dict(self):
        from shaaha.brain import Brain
        s = Brain().summary()
        assert "total_operations_recorded" in s
        assert "confidence" in s

    def test_timed_context_manager(self):
        import time
        from shaaha.brain import Brain
        b = Brain()
        with b.timed("math", "numpy"):
            time.sleep(0.01)
        ops = b._data["operations"]
        assert "math::numpy" in ops

    def test_reset_clears_data(self):
        from shaaha.brain import Brain
        b = Brain()
        b.record("math", "numpy", 5.0)
        b.reset()
        assert b._data["operations"] == {}

    def test_weight_boost_no_data(self):
        from shaaha.brain import Brain
        b = Brain()
        b.reset()
        boost = b.learned_weight_boost("math", "numpy")
        assert boost == 0  # not enough data

    def test_weight_boost_with_data(self):
        from shaaha.brain import Brain
        b = Brain()
        b.reset()
        for _ in range(10):
            b.record("testdom", "fast_lib", 1.0)
            b.record("testdom", "slow_lib", 50.0)
        boost_fast = b.learned_weight_boost("testdom", "fast_lib")
        boost_slow = b.learned_weight_boost("testdom", "slow_lib")
        assert boost_fast > boost_slow

# ═══════════════════════════════════════════════════════════════════════
# LAYER 5 — Self Healer
# ═══════════════════════════════════════════════════════════════════════
class TestHealer:
    def test_healer_singleton(self):
        from shaaha.healer import get_healer, Healer
        h = get_healer()
        assert isinstance(h, Healer)

    def test_history_starts_empty(self):
        from shaaha.healer import Healer
        h = Healer()
        assert isinstance(h.history(), list)

    def test_suppress_warnings_flag(self):
        import shaaha
        shaaha.suppress_warnings = True
        from shaaha import healer
        healer.suppress_warnings = True
        assert healer.suppress_warnings is True
        shaaha.suppress_warnings = False

# ═══════════════════════════════════════════════════════════════════════
# LAYER 6 — Explainer
# ═══════════════════════════════════════════════════════════════════════
class TestExplainer:
    def setup_method(self): _clean()

    def test_explain_detects_pandas(self, tmp_path):
        code = "import pandas as pd\ndf = pd.read_csv('data.csv')\n"
        f = tmp_path / "script.py"
        f.write_text(code)
        import shaaha
        result = shaaha.explain(str(f))
        assert "pandas" in result.lower()

    def test_explain_detects_numpy(self, tmp_path):
        code = "import numpy as np\narr = np.array([1,2,3])\n"
        f = tmp_path / "script.py"
        f.write_text(code)
        import shaaha
        result = shaaha.explain(str(f))
        assert "numpy" in result.lower()

    def test_explain_detects_anti_pattern(self, tmp_path):
        code = "for idx, row in df.iterrows():\n    print(row)\n"
        f = tmp_path / "script.py"
        f.write_text(code)
        from shaaha.explainer import Explainer
        exp = Explainer()
        anti = exp._detect_anti_patterns(code)
        assert len(anti) > 0

    def test_explain_file_not_found(self):
        import shaaha
        with pytest.raises(FileNotFoundError):
            shaaha.explain("nonexistent_file_xyz.py")

    def test_explain_saves_markdown(self, tmp_path):
        code = "import pandas as pd\n"
        f   = tmp_path / "script.py"
        out = tmp_path / "report.md"
        f.write_text(code)
        import shaaha
        shaaha.explain(str(f), output=str(out))
        assert out.exists()
        content = out.read_text()
        assert "#" in content   # has markdown headers

# ═══════════════════════════════════════════════════════════════════════
# LAYER 3 — Code Rewriter
# ═══════════════════════════════════════════════════════════════════════
class TestRewriter:
    def setup_method(self): _clean()

    def test_detects_pandas_import(self, tmp_path):
        code = "import pandas as pd\ndf = pd.read_csv('f.csv')\n"
        f = tmp_path / "s.py"
        f.write_text(code)
        from shaaha.rewriter import CodeRewriter
        rw = CodeRewriter(use_llm=False)
        changes = rw._rule_analyse(code)
        assert any("pandas" in c["pattern"] for c in changes)

    def test_detects_numpy_import(self, tmp_path):
        code = "import numpy as np\narr = np.zeros(100)\n"
        from shaaha.rewriter import CodeRewriter
        rw = CodeRewriter(use_llm=False)
        changes = rw._rule_analyse(code)
        assert any("numpy" in c["pattern"] for c in changes)

    def test_detects_iterrows_antipattern(self):
        code = "for idx, row in df.iterrows():\n    print(row)\n"
        from shaaha.rewriter import CodeRewriter
        rw = CodeRewriter(use_llm=False)
        changes = rw._rule_analyse(code)
        assert any("iterrows" in c.get("pattern","") for c in changes)

    def test_produces_rewritten_code(self, tmp_path):
        code = "import pandas as pd\ndf = pd.read_csv('data.csv')\n"
        f = tmp_path / "s.py"
        f.write_text(code)
        from shaaha.rewriter import CodeRewriter
        rw = CodeRewriter(use_llm=False)
        result = rw.optimize(str(f), auto_apply=False)
        assert "original" in result
        assert "rewritten" in result
        assert "shaaha" in result["rewritten"]

    def test_file_not_found(self):
        import shaaha
        with pytest.raises(FileNotFoundError):
            shaaha.optimize_file("no_such_file_xyz.py")

# ═══════════════════════════════════════════════════════════════════════
# LAYER 8 — Plugin System
# ═══════════════════════════════════════════════════════════════════════
class TestPlugins:
    def setup_method(self): _clean()

    def test_register_backend_adds_to_registry(self):
        import shaaha
        from shaaha.registry import REGISTRY
        shaaha.register_backend("dataframe", "testplugin", "json", priority=55)
        assert any(b.name == "testplugin" for b in REGISTRY.get("dataframe", []))

    def test_list_backends_runs(self, capsys):
        import shaaha
        shaaha.list_backends("math")
        captured = capsys.readouterr()
        assert "math" in captured.out.lower()

    def test_plugin_registry_singleton(self):
        from shaaha.plugins import PluginRegistry
        a, b = PluginRegistry(), PluginRegistry()
        assert a is b

# ═══════════════════════════════════════════════════════════════════════
# LAYER 9 — Collaboration
# ═══════════════════════════════════════════════════════════════════════
class TestCollab:
    def test_share_profile_creates_file(self, tmp_path):
        import shaaha
        out = tmp_path / "profile.json"
        shaaha.share_profile(str(out))
        assert out.exists()
        data = json.loads(out.read_text())
        assert "shaaha_version" in data
        assert "machine_summary" in data

    def test_import_profile_roundtrip(self, tmp_path):
        import shaaha
        from shaaha.brain import Brain
        Brain().reset()
        Brain().record("math", "numpy", 10.0)
        # Export
        out = tmp_path / "profile.json"
        shaaha.share_profile(str(out))
        # Reset and import
        Brain().reset()
        shaaha.import_profile(str(out))
        ops = Brain()._data.get("operations", {})
        assert len(ops) > 0

    def test_import_profile_file_not_found(self):
        import shaaha
        with pytest.raises(FileNotFoundError):
            shaaha.import_profile("no_such_profile_xyz.json")

# ═══════════════════════════════════════════════════════════════════════
# LAYER 10 — Safety Guard
# ═══════════════════════════════════════════════════════════════════════
class TestSafety:
    def setup_method(self): _clean()

    def test_safe_mode_toggle(self):
        import shaaha
        from shaaha import safety
        shaaha.safe_mode(True)
        assert safety.is_safe_mode() is True
        shaaha.safe_mode(False)
        assert safety.is_safe_mode() is False

    def test_verify_equivalence_matching_scalars(self):
        from shaaha.safety import verify_equivalence
        result = verify_equivalence(
            lambda: 42.0, lambda: 42.0,
            label_a="a", label_b="b"
        )
        assert result["match"] is True
        assert result["safe_to_switch"] is True

    def test_verify_equivalence_mismatching(self):
        from shaaha.safety import verify_equivalence
        result = verify_equivalence(
            lambda: 1.0, lambda: 2.0,
            label_a="a", label_b="b"
        )
        assert result["match"] is False

    def test_verify_numpy_arrays(self):
        import numpy as np
        from shaaha.safety import verify_equivalence
        a = np.array([1.0, 2.0, 3.0])
        result = verify_equivalence(
            lambda: a.copy(), lambda: a.copy(),
            label_a="a", label_b="b"
        )
        assert result["match"] is True

    def test_verify_numpy_arrays_differ(self):
        import numpy as np
        from shaaha.safety import verify_equivalence
        result = verify_equivalence(
            lambda: np.array([1.0, 2.0]), lambda: np.array([1.0, 9.0]),
            label_a="a", label_b="b"
        )
        assert result["match"] is False

# ═══════════════════════════════════════════════════════════════════════
# LAYER 2 — Agent (offline / fallback planner)
# ═══════════════════════════════════════════════════════════════════════
class TestAgent:
    def setup_method(self): _clean()

    def test_fallback_plan_generates_steps(self):
        from shaaha.agent import ShaahAgent
        ag = ShaahAgent()
        plan = ag._fallback_plan("load data.csv and plot a chart")
        assert "steps" in plan
        assert len(plan["steps"]) > 0

    def test_fallback_plan_detects_csv(self):
        from shaaha.agent import ShaahAgent
        ag = ShaahAgent()
        plan = ag._fallback_plan("analyse sales.csv")
        assert any("csv" in s["code"].lower() or "sales" in s["code"].lower()
                   for s in plan["steps"])

    def test_agent_run_returns_dict(self):
        import shaaha
        # No API key — uses fallback planner
        result = shaaha.agent("print hello world", api_key=None, save_report=False)
        assert "success" in result
        assert "steps_completed" in result

# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION — public API
# ═══════════════════════════════════════════════════════════════════════
class TestPublicAPIV2:
    def setup_method(self): _clean()

    def test_status_has_brain_confidence(self):
        import shaaha
        s = shaaha.status()
        assert "brain_confidence" in s
        assert "%" in s["brain_confidence"]

    def test_version_updated(self):
        import re
        import importlib.metadata
        import shaaha
        # Single-sourced from package metadata (pyproject.toml) — this test
        # should never need a manual bump again when the version changes.
        assert shaaha.__version__ == importlib.metadata.version("shaaha")
        assert re.match(r"^\d+\.\d+\.\d+", shaaha.__version__)

    def test_all_public_functions_exist(self):
        import shaaha
        for fn in ["configure","status","available_backends","agent",
                   "optimize_file","reset_learning","explain","dashboard",
                   "register_backend","list_backends","share_profile",
                   "import_profile","sync","safe_mode","safe_call"]:
            assert hasattr(shaaha, fn), f"Missing: shaaha.{fn}"
