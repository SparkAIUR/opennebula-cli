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


def ensure_assh_target(
    alias: str, endpoint: str, *, scope: str = "repo"
) -> subprocess.CompletedProcess[str]:
    """Upsert a reusable remote target alias in the sibling assh repo."""

    return run_assh("target", "add", alias, endpoint, "--scope", scope)


def probe_assh_environment() -> dict[str, object]:
    """Describe whether local read-only assh helpers can be used."""

    return {
        "available": has_assh_checkout(),
        "repo": str(ASSH_REPO),
        "uv": shutil.which("uv"),
    }


def run_readonly_probe(target: str) -> subprocess.CompletedProcess[str]:
    """Run a read-only status probe through the sibling assh checkout."""

    return run_assh("run", "uname -a && id && pwd", "--target", target)
