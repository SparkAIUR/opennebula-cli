"""Optional local wrappers around the sibling assh repo."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ASSH_REPO = Path("/Volumes/S0/github/_personal/assh")


def has_assh_checkout() -> bool:
    """Return true when the local dependency is present."""
    return ASSH_REPO.exists() and shutil.which("uv") is not None


def run_assh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the local assh CLI without making it a package dependency."""
    if not has_assh_checkout():
        raise RuntimeError("Local assh checkout is unavailable.")
    return subprocess.run(
        ["uv", "run", "assh", *args],
        cwd=ASSH_REPO,
        capture_output=True,
        check=True,
        text=True,
    )
