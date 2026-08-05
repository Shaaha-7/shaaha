"""
shaaha.explainer — Layer 6: The Explainer
==========================================
Reads a Python script and explains every library choice in plain English.
Educational tone — perfect for MSc students and researchers.

shaaha.explain("my_script.py")
shaaha.explain("my_script.py", output="report.md")
"""
from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("shaaha.explainer")

# ── Static knowledge base ─────────────────────────────────────────────────────
LIBRARY_EXPLANATIONS = {
    "pandas": {
        "what": "pandas is the standard Python library for tabular data (DataFrames).",
        "when_good": "Great for datasets under ~500MB and exploratory analysis.",
        "when_bad": "Slow on large files (>500MB). Single-threaded. High memory usage.",
        "shaaha_alternative": "shaaha.dataframe — auto-picks polars for big files (8x faster).",
        "speedup": "2-8x with polars on large datasets",
    },
    "numpy": {
        "what": "numpy is the foundation of scientific Python — fast array operations on CPU.",
        "when_good": "Excellent for CPU-based numerical computation. Universal compatibility.",
        "when_bad": "Does not use GPU. Single-threaded for many operations.",
        "shaaha_alternative": "shaaha.math — auto-picks cupy (GPU, 50x faster) or jax if available.",
        "speedup": "1-50x with cupy on GPU hardware",
    },
    "sklearn": {
        "what": "scikit-learn is the standard ML library — clean API, many algorithms.",
        "when_good": "Perfect for classical ML: regression, classification, clustering.",
        "when_bad": "CPU only. Slower than xgboost/lightgbm for gradient boosting.",
        "shaaha_alternative": "shaaha.ml — picks torch (GPU), xgboost, or sklearn automatically.",
        "speedup": "2-10x with GPU backends",
    },
    "matplotlib": {
        "what": "matplotlib is the original Python plotting library — highly customisable.",
        "when_good": "Publication-quality static charts. Supported everywhere.",
        "when_bad": "Static only. Complex API. Slow for large datasets.",
        "shaaha_alternative": "shaaha.viz — picks plotly (interactive) or seaborn automatically.",
        "speedup": "Better interactivity with plotly",
    },
    "requests": {
        "what": "requests is the standard HTTP library — simple and readable.",
        "when_good": "Simple synchronous HTTP calls. Very easy to use.",
        "when_bad": "Synchronous only — blocks while waiting. Slow for many requests.",
        "shaaha_alternative": "shaaha.http — picks httpx (async-ready, 5x faster for parallel requests).",
        "speedup": "2-5x for parallel HTTP requests with httpx",
    },
    "json": {
        "what": "json is Python's built-in JSON library — always available, no install.",
        "when_good": "Simple, always works, no dependencies.",
        "when_bad": "10x slower than orjson for large JSON files.",
        "shaaha_alternative": "shaaha.json — picks orjson (10x faster) or ujson automatically.",
        "speedup": "2-10x with orjson",
    },
    "cv2": {
        "what": "OpenCV (cv2) is the industry standard for computer vision and image processing.",
        "when_good": "Fastest for image processing, video, real-time CV tasks.",
        "when_bad": "Large install. Complex API for simple tasks.",
        "shaaha_alternative": "shaaha.image — picks cv2 if installed, falls back to Pillow.",
        "speedup": "2-3x vs Pillow for batch processing",
    },
    "torch": {
        "what": "PyTorch is a deep learning framework with GPU acceleration.",
        "when_good": "Deep learning, neural networks, GPU tensor operations.",
        "when_bad": "Large install (~2GB). Overkill for simple tasks.",
        "shaaha_alternative": "shaaha.ml — picks torch only when GPU is available and task needs it.",
        "speedup": "10-100x for deep learning tasks on GPU",
    },
    "polars": {
        "what": "polars is a modern, blazing-fast DataFrame library written in Rust.",
        "when_good": "Large datasets (>500MB). Multi-threaded. Memory efficient.",
        "when_bad": "Different API from pandas. Some pandas features missing.",
        "shaaha_alternative": "shaaha.dataframe already picks polars automatically for large data.",
        "speedup": "Already optimal!",
    },
}

ANTI_PATTERNS = [
    (r"for .+ in .+\.iterrows\(\)", "iterrows() loop",
     "iterrows() is one of the slowest pandas patterns. Use df.apply(), "
     "vectorised operations (df['col'] * 2), or df.itertuples() instead. "
     "Can be 100x slower than vectorised code."),
    (r"\.append\(.*\)\s*#.*loop|for .+:\s*\n.*\.append",
     "append() inside loop",
     "Building a list with append() in a loop then converting to DataFrame "
     "is slow. Use pd.concat() or build a list of dicts first."),
    (r"df\[.+\]\s*=\s*df\[.+\]\.apply\(lambda",
     "apply(lambda) on column",
     "apply(lambda) is slow because it runs Python one row at a time. "
     "Replace with vectorised operations: df['col'] * 2 instead of "
     "df['col'].apply(lambda x: x*2)."),
    (r"import \*",
     "wildcard import",
     "from module import * pollutes the namespace and makes code hard to read. "
     "Import only what you need."),
]


class Explainer:
    """Reads Python code and produces educational performance explanations."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def explain(self, filepath: str, output: Optional[str] = None,
                verbose: bool = True) -> str:
        """
        Explain all library choices in a Python file.

        Args:
            filepath: path to .py file
            output:   optional path to save markdown report
            verbose:  print to terminal

        Returns:
            Markdown string of the explanation
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"[Shaaha] File not found: {filepath}")

        code = path.read_text(encoding="utf-8")
        print(f"\n📖 [Shaaha Explainer] Analysing: {filepath}\n")

        report_lines = [
            f"# Shaaha Code Explanation Report",
            f"**File:** `{filepath}`",
            f"**Lines:** {len(code.splitlines())}",
            "",
        ]

        # 1 — Detect libraries
        findings = self._detect_libraries(code)
        anti     = self._detect_anti_patterns(code)

        # 2 — LLM enrichment if available
        llm_insights = self._llm_insights(code, filepath)

        # 3 — Build report
        if findings:
            report_lines += ["## 📦 Libraries Detected\n"]
            for lib, info in findings.items():
                block = [
                    f"### `import {lib}`",
                    f"**What it is:** {info['what']}",
                    f"**When it's good:** {info['when_good']}",
                    f"**Limitation:** {info['when_bad']}",
                    f"**Shaaha alternative:** {info['shaaha_alternative']}",
                    f"**Potential speedup:** ⚡ {info['speedup']}",
                    "",
                ]
                report_lines += block

        if anti:
            report_lines += ["## ⚠️ Anti-Patterns Detected\n"]
            for name, explanation in anti:
                report_lines += [
                    f"### ⚠️ `{name}`",
                    explanation,
                    "",
                ]

        if llm_insights:
            report_lines += ["## 🧠 AI Insights\n", llm_insights, ""]

        # 4 — Summary
        report_lines += [
            "## 💡 Quick Fix",
            "Replace your imports with shaaha equivalents:",
            "```python",
        ]
        for lib in findings:
            domain = self._lib_to_domain(lib)
            if domain:
                report_lines.append(f"import shaaha.{domain} as {lib}")
        report_lines += [
            "```",
            "",
            "---",
            "*Generated by Shaaha Explainer — pip install shaaha*",
        ]

        report_md = "\n".join(report_lines)

        if verbose:
            self._print_terminal(findings, anti, llm_insights)

        if output:
            Path(output).write_text(report_md, encoding="utf-8")
            print(f"\n📄 Report saved: {output}")

        return report_md

    def _detect_libraries(self, code: str) -> dict:
        found = {}
        for lib, info in LIBRARY_EXPLANATIONS.items():
            pattern = rf"\bimport {lib}\b|from {lib}\b"
            if re.search(pattern, code):
                found[lib] = info
        return found

    def _detect_anti_patterns(self, code: str) -> list[tuple]:
        found = []
        for pattern, name, explanation in ANTI_PATTERNS:
            if re.search(pattern, code):
                found.append((name, explanation))
        return found

    def _llm_insights(self, code: str, filepath: str) -> str:
        import os
        from shaaha._llm import call_claude

        api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return ""
        prompt = (
            f"Analyse this Python code and give 3 specific, actionable performance tips "
            f"in plain English. Focus on library choices and data handling patterns. "
            f"Be educational and encouraging. Code:\n```python\n{code[:2000]}\n```"
        )
        try:
            return call_claude(prompt, api_key, max_tokens=500, timeout=15)
        except Exception as e:
            logger.debug("LLM explainer failed: %s", e)
            return ""

    def _lib_to_domain(self, lib: str) -> Optional[str]:
        mapping = {
            "pandas": "dataframe", "numpy": "math", "sklearn": "ml",
            "matplotlib": "viz", "requests": "http", "json": "json",
            "cv2": "image", "torch": "ml", "polars": "dataframe",
        }
        return mapping.get(lib)

    def _print_terminal(self, findings: dict, anti: list, llm: str):
        if findings:
            print("📦 LIBRARIES FOUND:")
            for lib, info in findings.items():
                print(f"\n  import {lib}")
                print(f"    → {info['when_bad']}")
                print(f"    → Shaaha fix: {info['shaaha_alternative']}")
                print(f"    → Speedup: ⚡ {info['speedup']}")
        if anti:
            print("\n⚠️  ANTI-PATTERNS:")
            for name, exp in anti:
                print(f"\n  {name}")
                print(f"    {exp[:120]}...")
        if llm:
            print("\n🧠 AI INSIGHTS:")
            for line in llm.splitlines()[:10]:
                print(f"  {line}")


def explain(filepath: str, output: Optional[str] = None,
            api_key: Optional[str] = None) -> str:
    """
    Public API — explain all library choices in a Python file.

    Example:
        import shaaha
        shaaha.explain("my_analysis.py", output="report.md")
    """
    return Explainer(api_key=api_key).explain(filepath, output=output)
