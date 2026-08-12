from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    """Typer runner isolated from real operator credentials and state."""

    monkeypatch.setenv("OPENNEBULA_CLI_STATE_DB", str(tmp_path / "runner-state.db"))
    monkeypatch.setenv("OPENNEBULA_CLI_AUTH_CONFIG", str(tmp_path / "missing-auth.yaml"))
    monkeypatch.delenv("ONE_XMLRPC", raising=False)
    monkeypatch.delenv("ONE_AUTH", raising=False)
    return CliRunner()


@pytest.fixture
def state_env(tmp_path: Path) -> dict[str, str]:
    """Isolated state/auth environment for stateful CLI tests."""

    return {
        "OPENNEBULA_CLI_STATE_DB": str(tmp_path / "state.db"),
        "OPENNEBULA_CLI_AUTH_CONFIG": str(tmp_path / "missing-auth.yaml"),
    }
