"""
shaaha.rewriter — Layer 3: The Code Rewriter
=============================================
Reads a Python script, identifies slow patterns, rewrites using
faster backends, shows a before/after diff, NEVER applies without
user confirmation.

shaaha.optimize_file("my_script.py")
"""
from __future__ import annotations

import re
import ast
import json
import logging
import difflib
from pathlib import Path
from typing import Optional

logger = logging.getLogger("shaaha.rewriter")

# ── Rewrite rules ─────────────────────────────────────────────────────────────
# Each rule: (pattern_regex, replacement, speedup_estimate, reason)
REWRITE_RULES = [
    (
        r"import pandas as pd",
        "import shaaha.dataframe as pd",
        "2-8x",
        "Shaaha auto-selects polars (faster) or pandas based on data size",
    ),
    (
        r"import pandas",
        "import shaaha.dataframe as pandas",
        "2-8x",
        "Shaaha routes to polars for large files, pandas for small",
    ),
    (
        r"import numpy as np",
        "import shaaha.math as np",
        "1-50x",
        "Shaaha uses cupy on GPU (50x faster) or numpy on CPU — same API",
    ),
    (
        r"import numpy",
        "import shaaha.math as numpy",
        "1-50x",
        "Shaaha uses cupy on GPU or numpy on CPU automatically",
    ),
    (
        r"from sklearn import",
        "import shaaha.ml as _ml  # from sklearn import",
        "1-10x",
        "Shaaha uses torch/xgboost on GPU, sklearn on CPU",
    ),
    (
        r"import matplotlib\.pyplot as plt",
        "import shaaha.viz as plt",
        "1-3x",
        "Shaaha uses plotly (interactive) or matplotlib automatically",
    ),
    (
        r"import cv2",
        "import shaaha.image as cv2",
        "1-2x",
        "Shaaha uses opencv or pillow based on what is installed",
    ),
    (
        r"import requests",
        "import shaaha.http as requests",
        "1-5x",
        "Shaaha uses httpx (async-ready) or requests automatically",
    ),
    (
        r"import json\b",
        "import shaaha.json as json",
        "2-10x",
        "Shaaha uses orjson (10x faster) or ujson when available",
    ),
    (
        r"pd\.read_csv\(",
        "pd.read_csv(",
        None,  # already handled by import swap
        None,
    ),
    (
        r"df\.iterrows\(\)",
        "# SLOW: iterrows() — consider df.apply() or vectorised ops",
        "10-100x",
        "iterrows() is the slowest pandas pattern — vectorise instead",
    ),
    (
        r"for .+ in df\.iterrows",
        "# WARNING: iterrows loop detected — replace with vectorised operation",
        "10-100x",
        "Loop over iterrows is extremely slow for large dataframes",
    ),
]


class CodeRewriter:
    """Analyses and rewrites Python scripts for maximum performance."""

    def __init__(self, use_llm: bool = True, api_key: Optional[str] = None):
        self.use_llm = use_llm
        self.api_key = api_key

    def optimize(self, filepath: str, auto_apply: bool = False) -> dict:
        """
        Analyse a Python file and suggest/apply optimisations.

        Args:
            filepath:   path to the .py file
            auto_apply: if True, apply changes without asking (dangerous!)

        Returns:
            dict with keys: original, rewritten, changes, speedup_summary
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"[Shaaha] File not found: {filepath}")

        original = path.read_text(encoding="utf-8")
        print(f"\n🔍 [Shaaha Rewriter] Analysing: {filepath}")
        print(f"   Lines: {len(original.splitlines())} | Size: {len(original)} bytes\n")

        # Get changes from LLM or rule engine
        if self.use_llm:
            changes = self._llm_analyse(original, filepath)
        else:
            changes = self._rule_analyse(original)

        if not changes:
            print("✅ No optimisations found — your code looks good!")
            return {"original": original, "rewritten": original,
                    "changes": [], "speedup_summary": "No changes needed"}

        # Apply changes to produce rewritten version
        rewritten = original
        for change in changes:
            if change.get("pattern") and change.get("replacement"):
                rewritten = re.sub(
                    change["pattern"], change["replacement"],
                    rewritten, count=1
                )

        # Show diff
        self._print_diff(original, rewritten)
        self._print_change_table(changes)

        speedup = self._summarise_speedup(changes)
        print(f"\n⚡ Estimated overall speedup: {speedup}")

        # Ask for confirmation
        if not auto_apply:
            try:
                answer = input(
                    f"\n💾 Apply these changes to '{filepath}'? [y/N]: "
                ).strip().lower()
            except (EOFError, OSError):
                answer = "n"

            if answer not in ("y", "yes"):
                print("   Changes NOT applied. Rewritten code returned for review.")
                # Save to a suggestion file instead
                suggest_path = path.with_suffix(".shaaha_optimized.py")
                suggest_path.write_text(rewritten, encoding="utf-8")
                print(f"   Suggestion saved to: {suggest_path}")
            else:
                # Backup original
                backup = path.with_suffix(".py.shaaha_backup")
                backup.write_text(original, encoding="utf-8")
                path.write_text(rewritten, encoding="utf-8")
                print(f"   ✅ Applied! Backup saved to: {backup}")
        else:
            backup = path.with_suffix(".py.shaaha_backup")
            backup.write_text(original, encoding="utf-8")
            path.write_text(rewritten, encoding="utf-8")

        return {
            "original": original,
            "rewritten": rewritten,
            "changes": changes,
            "speedup_summary": speedup,
        }

    def _rule_analyse(self, code: str) -> list[dict]:
        """Apply static rewrite rules — no LLM needed."""
        changes = []
        for pattern, replacement, speedup, reason in REWRITE_RULES:
            if re.search(pattern, code) and reason:  # skip comment-only rules
                changes.append({
                    "pattern": pattern,
                    "replacement": replacement,
                    "speedup": speedup or "unknown",
                    "reason": reason,
                })
        return changes

    def _llm_analyse(self, code: str, filepath: str) -> list[dict]:
        """Ask Claude to find optimisations beyond static rules."""
        import os, urllib.request

        api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.info("No API key — falling back to rule-based analysis")
            return self._rule_analyse(code)

        prompt = f"""You are a Python performance expert. Analyse this Python script and identify
optimisations by replacing standard libraries with shaaha equivalents.

FILE: {filepath}
CODE:
```python
{code[:3000]}
```

Respond ONLY with JSON array of changes:
[
  {{
    "pattern": "regex pattern to find",
    "replacement": "replacement string",
    "speedup": "e.g. 5x",
    "reason": "plain English explanation"
  }}
]

Focus on: pandas→shaaha.dataframe, numpy→shaaha.math, sklearn→shaaha.ml,
matplotlib→shaaha.viz, requests→shaaha.http, json→shaaha.json.
Also flag: iterrows loops, unnecessary copies, non-vectorised operations.
Return [] if no changes needed."""

        try:
            payload = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}],
            }).encode()

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
                text = data["content"][0]["text"].strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return json.loads(text.strip())
        except Exception as e:
            logger.warning("LLM rewriter failed: %s — using rules", e)
            return self._rule_analyse(code)

    def _print_diff(self, original: str, rewritten: str):
        """Print a coloured unified diff."""
        orig_lines = original.splitlines(keepends=True)
        new_lines  = rewritten.splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            orig_lines, new_lines,
            fromfile="original", tofile="optimized", n=2
        ))
        if diff:
            print("─" * 60)
            print("DIFF (original → optimized):")
            print("─" * 60)
            for line in diff[:60]:   # cap at 60 lines
                if line.startswith("+") and not line.startswith("+++"):
                    print(f"  \033[92m{line}\033[0m", end="")
                elif line.startswith("-") and not line.startswith("---"):
                    print(f"  \033[91m{line}\033[0m", end="")
                else:
                    print(f"  {line}", end="")
            print("\n" + "─" * 60)

    def _print_change_table(self, changes: list[dict]):
        """Print a summary table of all changes."""
        print("\n📊 Optimisations found:\n")
        for i, c in enumerate(changes, 1):
            print(f"  {i}. [{c.get('speedup','?')} speedup] {c.get('reason','')}")

    def _summarise_speedup(self, changes: list[dict]) -> str:
        """Pick the most impactful speedup from all changes."""
        speedups = [c.get("speedup", "") for c in changes if c.get("speedup")]
        if not speedups:
            return "unknown"
        # Extract max multiplier
        import re as _re
        maxes = []
        for s in speedups:
            nums = _re.findall(r'\d+', s)
            if nums:
                maxes.append(int(nums[-1]))
        return f"up to {max(maxes)}x faster" if maxes else speedups[0]


def optimize_file(filepath: str, auto_apply: bool = False,
                  use_llm: bool = True, api_key: Optional[str] = None) -> dict:
    """
    Public API — analyse and optionally rewrite a Python file.

    Example:
        import shaaha
        shaaha.optimize_file("analysis.py")
    """
    rw = CodeRewriter(use_llm=use_llm, api_key=api_key)
    return rw.optimize(filepath, auto_apply=auto_apply)
