"""
shaaha.brain — Layer 4: The Adaptive Brain
==========================================
Records every backend operation's timing locally.
After enough runs, learns which backend is genuinely fastest on THIS machine
and adjusts routing weights automatically.

Storage: ~/.shaaha/profile.json
"""
from __future__ import annotations

import json
import time
import logging
import statistics
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger("shaaha.brain")

_PROFILE_DIR  = Path.home() / ".shaaha"
_PROFILE_FILE = _PROFILE_DIR / "profile.json"
_MIN_SAMPLES  = 5   # minimum runs before brain overrides registry weights


class Brain:
    """Adaptive learning engine — observes, records, and improves over time."""

    _instance: Optional["Brain"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = cls._instance._load()
        return cls._instance

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        try:
            _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            if _PROFILE_FILE.exists():
                return json.loads(_PROFILE_FILE.read_text())
        except Exception as e:
            logger.warning("Brain: could not load profile: %s", e)
        return {"version": "2.0", "operations": {}, "created": datetime.now().isoformat()}

    def _save(self):
        try:
            _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            _PROFILE_FILE.write_text(json.dumps(self._data, indent=2))
        except Exception as e:
            logger.warning("Brain: could not save profile: %s", e)

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(self, domain: str, backend: str, elapsed_ms: float):
        """Record a completed operation's timing."""
        key = f"{domain}::{backend}"
        ops = self._data.setdefault("operations", {})
        entry = ops.setdefault(key, {"domain": domain, "backend": backend,
                                     "timings": [], "count": 0})
        entry["timings"].append(round(elapsed_ms, 3))
        entry["timings"] = entry["timings"][-100:]   # keep last 100
        entry["count"] += 1
        entry["last_seen"] = datetime.now().isoformat()
        self._save()
        logger.debug("Brain recorded: %s → %.2fms", key, elapsed_ms)

    @contextmanager
    def timed(self, domain: str, backend: str):
        """Context manager — automatically records timing."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            self.record(domain, backend, elapsed)

    # ── Learning ──────────────────────────────────────────────────────────────

    def learned_weight_boost(self, domain: str, backend: str) -> int:
        """
        Return a score boost (+/-) based on learned performance.
        Returns 0 if not enough data yet.
        """
        ops = self._data.get("operations", {})
        domain_entries = {
            k: v for k, v in ops.items()
            if v["domain"] == domain and len(v["timings"]) >= _MIN_SAMPLES
        }
        if not domain_entries or f"{domain}::{backend}" not in domain_entries:
            return 0

        # Median timing for each backend in this domain
        medians = {
            k: statistics.median(v["timings"])
            for k, v in domain_entries.items()
        }
        my_key    = f"{domain}::{backend}"
        my_median = medians[my_key]
        best_median = min(medians.values())

        if my_median == best_median:
            return 15   # boost the fastest
        elif my_median < statistics.mean(medians.values()):
            return 5    # small boost for above-average
        else:
            return -10  # penalise slow backends

    def confidence(self) -> float:
        """0.0–1.0 — how much data the brain has learned from."""
        ops = self._data.get("operations", {})
        if not ops:
            return 0.0
        total   = sum(e["count"] for e in ops.values())
        mature  = sum(1 for e in ops.values() if e["count"] >= _MIN_SAMPLES)
        return min(1.0, (total / 50) * 0.5 + (mature / max(len(ops), 1)) * 0.5)

    def summary(self) -> dict:
        """Return a human-readable learning summary."""
        ops = self._data.get("operations", {})
        result = {
            "total_operations_recorded": sum(e["count"] for e in ops.values()),
            "domains_learned": len({e["domain"] for e in ops.values()}),
            "confidence": f"{self.confidence()*100:.0f}%",
            "recommendations": [],
        }
        # Find best backend per domain
        domain_medians: dict = {}
        for k, v in ops.items():
            if len(v["timings"]) >= _MIN_SAMPLES:
                med = statistics.median(v["timings"])
                domain_medians.setdefault(v["domain"], []).append(
                    (v["backend"], med)
                )
        for domain, entries in domain_medians.items():
            entries.sort(key=lambda x: x[1])
            best_name, best_ms = entries[0]
            result["recommendations"].append(
                f"{domain}: '{best_name}' is fastest on your machine "
                f"(median {best_ms:.1f}ms)"
            )
        return result

    def reset(self):
        """Clear all learned data."""
        self._data = {"version": "2.0", "operations": {}, "created": datetime.now().isoformat()}
        self._save()
        logger.info("Brain reset — all learned data cleared.")
        print("[Shaaha Brain] Learning data cleared.")
