"""
shaaha.installer
================
Phase 3 — Optional Auto-Installer.

When auto_install=True and a backend is missing, Shaaha can
pip-install it on-the-fly with user consent.
"""

from __future__ import annotations

import sys
import logging
import subprocess
import importlib.util

logger = logging.getLogger("shaaha.installer")


class Installer:
    """Handles on-demand pip installation of missing backends."""

    _already_tried: set = set()

    @classmethod
    def install(cls, package: str, ask_user: bool = True) -> bool:
        """
        Attempt to pip-install `package`.

        Args:
            package:   pip package name.
            ask_user:  if True, prompt user before installing.

        Returns:
            True if the package is importable after install attempt.
        """
        if package in cls._already_tried:
            return importlib.util.find_spec(package) is not None

        cls._already_tried.add(package)

        if importlib.util.find_spec(package) is not None:
            return True

        if ask_user:
            try:
                answer = input(
                    f"\n[Shaaha] The optimal backend '{package}' is not installed.\n"
                    f"  Install it now? [y/N]: "
                ).strip().lower()
            except (EOFError, OSError):
                # Non-interactive environment
                answer = "n"

            if answer not in ("y", "yes"):
                logger.info("User declined install of '%s'", package)
                return False

        logger.info("Installing '%s' via pip...", package)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package, "--quiet"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("Successfully installed '%s'", package)
            # Refresh importlib cache
            importlib.invalidate_caches()
            return importlib.util.find_spec(package) is not None
        else:
            logger.error(
                "Failed to install '%s': %s", package, result.stderr.strip()
            )
            return False
