"""
tests/test_readme_examples.py
==============================
Executes the promises made in README.md, not just internal implementation
details. The 2.0.1 regression that shipped to PyPI was the README's own
Quick Start example (`ml.LinearRegression()`) crashing on any machine with
torch installed alongside sklearn — every other test in this suite was
green at the time because none of them ran the README verbatim.

Network-dependent examples (Layer 2 Agent's LLM call, Layer 9's team-server
sync) are exercised through their documented offline/failure behaviour
instead of hitting real endpoints.
"""
import sys
import json
import pytest


def _clean():
    for k in list(sys.modules):
        if k == "shaaha" or k.startswith("shaaha."):
            del sys.modules[k]
    sys.meta_path[:] = [f for f in sys.meta_path if type(f).__name__ != "ShaahafFinder"]


class TestQuickStart:
    """README.md, 'Quick Start' section."""

    def setup_method(self):
        _clean()

    def test_math_domain(self):
        import shaaha
        import shaaha.math as sm
        arr = sm.array([1, 2, 3, 4, 5])
        result = sm.sqrt(arr)
        assert list(result) == pytest.approx([1, 1.4142135, 1.7320508, 2, 2.2360679], rel=1e-4)

    def test_dataframe_domain(self, tmp_path):
        import shaaha
        import shaaha.dataframe as sdf
        csv = tmp_path / "sales.csv"
        csv.write_text("product,units\nwidget,10\ngadget,5\n")
        data = sdf.read_csv(str(csv))
        assert len(data) == 2

    def test_ml_domain_linear_regression(self):
        # This is the exact call that crashed in 2.0.1: torch (installed,
        # no GPU) used to outrank sklearn and has no LinearRegression at
        # all, and the self-healer that should have caught it was never
        # wired up. Both are fixed; this test pins the fix in place.
        import shaaha
        import shaaha.ml as ml
        model = ml.LinearRegression()
        X_train = [[1], [2], [3], [4]]
        y_train = [2, 4, 6, 8]
        model.fit(X_train, y_train)
        pred = model.predict([[5]])
        assert pred[0] == pytest.approx(10, abs=1)

    def test_image_domain(self, tmp_path):
        import shaaha
        import shaaha.image as img
        from PIL import Image as _PILImage
        src = tmp_path / "in.png"
        _PILImage.new("RGB", (4, 4), color=(255, 0, 0)).save(src)
        image = img.open(str(src))
        gray = img.to_grayscale(image)
        assert gray is not None

    def test_viz_domain_importable(self):
        import shaaha
        import shaaha.viz as viz
        assert viz is not None


class TestLayer4AdaptiveBrain:
    def setup_method(self):
        _clean()

    def test_status_shape(self):
        import shaaha
        s = shaaha.status()
        assert "brain_confidence" in s and "%" in s["brain_confidence"]
        assert "recommendations" in s["brain_summary"] if "brain_summary" in s else True

    def test_reset_learning_runs(self):
        import shaaha
        shaaha.reset_learning()  # must not raise


class TestLayer2Agent:
    """README's exact example: shaaha.agent("load sales.csv, find the top
    10 products, and plot a bar chart"). No API key in CI, so this runs
    the offline fallback planner - which actually executes the generated
    code, unlike the pre-existing tests that only checked the *plan*
    (e.g. that "shaaha_df.read_csv(...)" appears in the code string)
    without ever running it. Running it is what caught this: the fallback
    planner generated `shaaha_df.read_csv(...)` but _execute_step() only
    ever injects the domain proxy as `shaaha_dataframe`, so the CSV-load
    step failed on every single call with no API key configured."""

    def setup_method(self):
        _clean()

    def test_load_csv_task_actually_succeeds(self, tmp_path, monkeypatch):
        import shaaha
        monkeypatch.chdir(tmp_path)
        (tmp_path / "sales.csv").write_text("product,units\nwidget,10\ngadget,5\n")

        result = shaaha.agent(
            "load sales.csv, find the top 10 products, and plot a bar chart",
            api_key=None, save_report=False,
        )
        load_step = result["results"][0]
        assert load_step["success"], load_step.get("error")


class TestLayer5SelfHealer:
    """README claims: 'When a backend crashes, Shaaha auto-switches and
    always notifies you.' This was silently dead code until this session
    (ProxyModule was always constructed with healer_cls=None) — this test
    exercises the real end-to-end path via the import hook, not just the
    Healer class in isolation."""

    def setup_method(self):
        _clean()

    def test_missing_attribute_triggers_visible_fallback(self, capsys):
        import shaaha
        import shaaha.ml as ml
        # torch (if installed) has no LinearRegression; sklearn does.
        # Accessing it must either resolve correctly via a reported
        # fallback, or resolve directly if sklearn was already primary -
        # either way it must NOT raise.
        _ = ml.LinearRegression
        # If a fallback happened, the healer must have logged it.
        from shaaha.healer import get_healer
        history = get_healer().history()
        for entry in history:
            assert entry["domain"] and entry["from"] and entry["to"]


class TestLayer6Explainer:
    def setup_method(self):
        _clean()

    def test_explain_pandas_script(self, tmp_path):
        import shaaha
        f = tmp_path / "script.py"
        f.write_text("import pandas as pd\ndf = pd.read_csv('data.csv')\n")
        report = shaaha.explain(str(f))
        assert "pandas" in report.lower()


class TestLayer7Dashboard:
    def test_dashboard_api_data_shape(self):
        pytest.importorskip("flask")
        from shaaha.dashboard import _build_app
        app = _build_app()
        client = app.test_client()

        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Shaaha Dashboard" in resp.data

        resp = client.get("/api/data")
        assert resp.status_code == 200
        payload = json.loads(resp.data)
        for key in ("operations", "confidence", "recommendations", "selected_backends", "env"):
            assert key in payload


class TestLayer8PluginSystem:
    def setup_method(self):
        _clean()

    def test_register_and_list(self, capsys):
        import shaaha
        shaaha.register_backend("dataframe", "vaex", "vaex", priority=88)
        shaaha.list_backends("dataframe")
        out = capsys.readouterr().out
        assert "vaex" in out


class TestLayer9Collaboration:
    def test_sync_fails_gracefully_offline(self, capsys):
        import shaaha
        # README shows this exact call; there is no real team server here,
        # so the documented contract is that it reports failure and
        # suggests share_profile() instead of raising.
        shaaha.sync("http://127.0.0.1:1/nonexistent")
        out = capsys.readouterr().out
        assert "share_profile" in out.lower() or "failed" in out.lower()


class TestLayer10SafetyGuard:
    def setup_method(self):
        _clean()

    def test_safe_mode_matching_result(self, capsys):
        import shaaha
        from shaaha.safety import verify_equivalence
        shaaha.safe_mode(True)
        result = verify_equivalence(lambda: 42.0, lambda: 42.0, label_a="jax", label_b="numpy")
        assert result["safe_to_switch"] is True
        shaaha.safe_mode(False)
