"""Version metadata helpers for CLI display."""

from __future__ import annotations

import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from opennebula_cli import __version__
from opennebula_cli._build import BUILD_GIT_HASH


def app_version() -> str:
    """Return installed package version, or source fallback."""

    try:
        return version("opennebula-cli")
    except PackageNotFoundError:
        return __version__


def git_hash() -> str:
    """Return build-time git hash, or derive local repository hash."""

    stamped = BUILD_GIT_HASH.strip()
    if stamped and stamped.lower() != "unknown":
        return stamped

    repository_root = Path(__file__).resolve().parents[2]
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"

    derived = completed.stdout.strip()
    return derived or "unknown"
