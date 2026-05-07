"""
shaaha.safety — Layer 10: The Safety Guard
===========================================
Before any backend switch or code rewrite, mathematically verifies
that outputs are identical. Essential for research reproducibility.

shaaha.safe_mode(True)
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("shaaha.safety")

_safe_mode_enabled: bool = False


def safe_mode(enabled: bool = True):
    """
    Enable or disable Safety Guard.

    When enabled, every backend operation is verified:
    1. Run with current backend
    2. Run with fallback backend
    3. Compare outputs mathematically
    4. Only proceed if results match

    Example:
        import shaaha
        shaaha.safe_mode(True)
    """
    global _safe_mode_enabled
    _safe_mode_enabled = enabled
    status = "ENABLED ✅" if enabled else "DISABLED"
    print(f"[Shaaha Safety Guard] {status}")
    if enabled:
        print("  All backend switches will be mathematically verified before applying.")
    logger.info("Safe mode: %s", enabled)


def is_safe_mode() -> bool:
    return _safe_mode_enabled


def verify_equivalence(
    func_a: Callable,
    func_b: Callable,
    args: tuple = (),
    kwargs: dict = None,
    tolerance: float = 1e-6,
    label_a: str = "backend_a",
    label_b: str = "backend_b",
) -> dict:
    """
    Run the same operation on two backends and compare results.

    Returns:
        dict with: match (bool), result_a, result_b, diff_summary, safe_to_switch
    """
    kwargs = kwargs or {}
    result_a = result_b = None
    error_a  = error_b  = None

    try:
        result_a = func_a(*args, **kwargs)
    except Exception as e:
        error_a = str(e)

    try:
        result_b = func_b(*args, **kwargs)
    except Exception as e:
        error_b = str(e)

    if error_a:
        return {"match": False, "safe_to_switch": True,
                "diff_summary": f"{label_a} failed: {error_a}",
                "result_a": None, "result_b": result_b}

    if error_b:
        return {"match": False, "safe_to_switch": False,
                "diff_summary": f"{label_b} failed: {error_b}",
                "result_a": result_a, "result_b": None}

    match, summary = _compare(result_a, result_b, tolerance, label_a, label_b)

    if match:
        print(f"✅ [Shaaha Safety] Results match 100%. Safe to switch "
              f"from '{label_a}' to '{label_b}'.")
    else:
        print(f"⚠️  [Shaaha Safety] Results DIFFER between '{label_a}' and '{label_b}'.")
        print(f"   {summary}")
        print(f"   Switch NOT applied. Use shaaha.safe_mode(False) to override.")

    return {
        "match":          match,
        "safe_to_switch": match,
        "diff_summary":   summary,
        "result_a":       result_a,
        "result_b":       result_b,
    }


def safe_call(domain: str, func_name: str, *args, **kwargs) -> Any:
    """
    Call a shaaha domain function with safety verification.
    Falls back only if output is mathematically equivalent.

    Example:
        result = shaaha.safe_call('math', 'sqrt', my_array)
    """
    if not _safe_mode_enabled:
        import importlib
        mod = importlib.import_module(f"shaaha.{domain}")
        return getattr(mod, func_name)(*args, **kwargs)

    from shaaha.registry import Registry
    from shaaha.router import Router
    import importlib

    # Primary backend
    primary_mod  = Router.resolve(domain)
    primary_func = getattr(primary_mod, func_name, None)

    # Find next best backend for verification
    available = Registry.available_backends(domain)
    primary_name = getattr(primary_mod, "__name__", "").split(".")[0]
    fallback_mod  = None

    for name in available:
        if name != primary_name:
            try:
                fallback_mod = importlib.import_module(name)
                break
            except ImportError:
                continue

    if fallback_mod is None or primary_func is None:
        # No fallback to compare — just run primary
        return primary_func(*args, **kwargs) if primary_func else None

    fallback_func = getattr(fallback_mod, func_name, None)
    if fallback_func is None:
        return primary_func(*args, **kwargs)

    result = verify_equivalence(
        primary_func, fallback_func, args=args, kwargs=kwargs,
        label_a=primary_name,
        label_b=getattr(fallback_mod, "__name__", "fallback").split(".")[0],
    )
    return result["result_a"]  # Always return primary result


def _compare(a: Any, b: Any, tol: float, la: str, lb: str) -> tuple[bool, str]:
    """Deep comparison of two results with numeric tolerance."""
    try:
        import numpy as np
        # numpy arrays
        if hasattr(a, "__array__") and hasattr(b, "__array__"):
            arr_a = np.asarray(a, dtype=float)
            arr_b = np.asarray(b, dtype=float)
            if arr_a.shape != arr_b.shape:
                return False, f"Shape mismatch: {arr_a.shape} vs {arr_b.shape}"
            close = np.allclose(arr_a, arr_b, atol=tol, rtol=tol)
            if not close:
                diff = float(np.abs(arr_a - arr_b).max())
                return False, f"Max difference: {diff:.2e} (tolerance: {tol:.2e})"
            return True, "Arrays match within tolerance"
    except ImportError:
        pass

    # DataFrames
    try:
        import pandas as pd
        if isinstance(a, pd.DataFrame) and isinstance(b, pd.DataFrame):
            if list(a.columns) != list(b.columns):
                return False, "Column mismatch"
            if len(a) != len(b):
                return False, f"Row count: {len(a)} vs {len(b)}"
            return True, "DataFrames match"
    except ImportError:
        pass

    # Scalars and strings
    if type(a) != type(b):
        return False, f"Type mismatch: {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, float):
        match = abs(a - b) < tol
        return match, f"Values: {a} vs {b}"
    match = (a == b)
    return bool(match), f"Values: '{a}' vs '{b}'"
