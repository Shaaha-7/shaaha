"""
tests/test_domain_contracts.py
================================
Behavioural contracts for naturally-routed domains (no force_backend).

These deliberately do NOT assert which backend gets picked - that's an
implementation detail that legitimately varies by machine/installed
packages. Instead they assert the observable contract Shaaha promises
("shaaha.ml behaves like a classical-ML API, whatever library it is")
actually holds for whatever the router picked. This is the class of test
that would have caught the LinearRegression bug automatically instead of
requiring a manual repro against the README.
"""
import sys
import pytest


def _clean():
    for k in list(sys.modules):
        if k == "shaaha" or k.startswith("shaaha."):
            del sys.modules[k]
    sys.meta_path[:] = [f for f in sys.meta_path if type(f).__name__ != "ShaahafFinder"]


class TestMathContract:
    def setup_method(self):
        _clean()

    def test_array_roundtrips_to_python_list(self):
        import shaaha
        import shaaha.math as sm
        assert list(sm.array([1, 2, 3])) == [1, 2, 3]

    def test_elementwise_sqrt(self):
        import shaaha
        import shaaha.math as sm
        result = list(sm.sqrt(sm.array([4.0, 9.0, 16.0])))
        assert result == pytest.approx([2.0, 3.0, 4.0])


class TestDataframeContract:
    def setup_method(self):
        _clean()

    def test_read_csv_row_and_column_access(self, tmp_path):
        import shaaha
        import shaaha.dataframe as sdf
        csv = tmp_path / "t.csv"
        csv.write_text("product,units\nwidget,10\ngadget,5\nwhatsit,7\n")
        data = sdf.read_csv(str(csv))
        assert len(data) == 3
        assert "product" in list(data.columns)


class TestMlContract:
    """The domain where "same API" is most likely to be false - torch and
    xgboost/lightgbm don't implement sklearn's estimator API at all, so
    natural routing here is the sharpest test of the self-healer."""

    def setup_method(self):
        _clean()

    def test_linear_regression_fit_predict(self):
        import shaaha
        import shaaha.ml as ml
        model = ml.LinearRegression()
        model.fit([[1], [2], [3], [4]], [2, 4, 6, 8])
        assert model.predict([[10]])[0] == pytest.approx(20, abs=2)

    def test_train_test_split_callable(self):
        import shaaha
        import shaaha.ml as ml
        X_train, X_test, y_train, y_test = ml.train_test_split(
            [[1], [2], [3], [4]], [1, 2, 3, 4], test_size=0.5, random_state=0
        )
        assert len(X_train) + len(X_test) == 4


class TestImageContract:
    def setup_method(self):
        _clean()

    def test_open_grayscale_array_roundtrip(self, tmp_path):
        import shaaha
        import shaaha.image as img
        from PIL import Image as _PILImage

        src = tmp_path / "in.png"
        _PILImage.new("RGB", (4, 4), color=(10, 20, 30)).save(src)

        image = img.open(str(src))
        gray = img.to_grayscale(image)
        arr = img.to_array(gray)
        assert arr.shape[:2] == (4, 4)


class TestJsonContract:
    """json always has the stdlib json module as a guaranteed fallback -
    this must pass even with zero optional dependencies installed."""

    def setup_method(self):
        _clean()

    def test_dumps_loads_roundtrip(self):
        import shaaha
        import shaaha.json as sjson
        payload = {"a": 1, "b": [1, 2, 3]}
        assert sjson.loads(sjson.dumps(payload)) == payload
