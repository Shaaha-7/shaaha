"""
shaaha.healer — Layer 5: The Self-Healer
=========================================
When a backend crashes or raises AttributeError, the healer silently
tries the next available backend — but ALWAYS notifies the user.

Philosophy: Never hide failures silently. Always tell the user what switched.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("shaaha.healer")

# Global flag — set by shaaha.suppress_warnings = True
suppress_warnings: bool = False


class Healer:
    """Catches backend failures and attempts graceful fallback."""

    def __init__(self):
        self._fallback_log: list[dict] = []

    def try_fallback(self, domain: str, failed_attr: str) -> Optional[Any]:
        """
        Try the next available backend for `domain` after current one failed.

        Returns the new backend module, or None if no fallback exists.
        Always prints a warning unless suppress_warnings is True.
        """
        from shaaha.registry import Registry
        from shaaha.router import Router
        from shaaha.environment import Environment

        env = Environment.probe()
        available = Registry.available_backends(domain)

        # Get current backend name
        current = Router._cache.get(domain)
        current_name = getattr(current, "__name__", "").split(".")[0] if current else ""

        # Find next backend (skip current)
        for candidate_name in available:
            if candidate_name == current_name:
                continue
            try:
                import importlib
                mod = importlib.import_module(candidate_name)

                # Log the switch
                msg = (
                    f"[Shaaha] '{current_name}' failed on attribute '{failed_attr}' "
                    f"→ switched to '{candidate_name}'.\n"
                    f"  To suppress this warning: import shaaha; shaaha.suppress_warnings = True"
                )
                self._fallback_log.append({
                    "domain": domain,
                    "from": current_name,
                    "to": candidate_name,
                    "reason": f"missing attribute: {failed_attr}",
                })

                if not suppress_warnings:
                    print(f"\n⚠️  {msg}\n")
                logger.warning(msg)

                # Update router cache with new backend
                Router._cache[domain] = mod
                return mod

            except ImportError:
                continue

        return None

    def wrap(self, domain: str, backend_name: str, func, *args, **kwargs):
        """
        Call func(*args, **kwargs) and auto-heal if it raises.
        Used by the timed brain wrapper.
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning("Healer caught error in '%s': %s", backend_name, e)
            fallback = self.try_fallback(domain, str(e))
            if fallback:
                # Retry with same args on new backend
                new_func = getattr(fallback, func.__name__, None)
                if new_func:
                    return new_func(*args, **kwargs)
            raise

    def history(self) -> list[dict]:
        """Return the list of all fallback events this session."""
        return list(self._fallback_log)


# Module-level singleton
_healer = Healer()


def get_healer() -> Healer:
    return _healer
