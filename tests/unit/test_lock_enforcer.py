from __future__ import annotations

from pathlib import Path

import pytest

from opennebula_cli.lock_enforcer import ensure_command_allowed, normalize_action, parse_invocation
from opennebula_cli.state_store import StateStore


def test_parse_invocation_strips_global_options() -> None:
    parsed = parse_invocation(["--output", "json", "--profile=prod", "vm", "list"])

    assert parsed.command == "vm"
    assert parsed.action == "list"


def test_normalize_action_maps_common_tokens() -> None:
    assert normalize_action("list") == "list"
    assert normalize_action("show") == "show"
    assert normalize_action("instantiate") == "create"
    assert normalize_action("delete") == "delete"
    assert normalize_action("reboot") == "update"


def test_ensure_command_allowed_blocks_matching_lock(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    monkeypatch.setenv("OPENNEBULA_CLI_STATE_DB", str(db))
    StateStore().set_lock(actions={"all"}, commands={"vm"}, password=None)

    with pytest.raises(RuntimeError, match="Command is locked"):
        ensure_command_allowed(["vm", "list"])


def test_ensure_command_allowed_allows_non_matching_action(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    monkeypatch.setenv("OPENNEBULA_CLI_STATE_DB", str(db))
    StateStore().set_lock(actions={"delete"}, commands={"vm"}, password=None)

    ensure_command_allowed(["vm", "show", "42"])


def test_ensure_command_allowed_bypasses_state_group(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    monkeypatch.setenv("OPENNEBULA_CLI_STATE_DB", str(db))
    StateStore().set_lock(actions={"all"}, commands={"all"}, password=None)

    ensure_command_allowed(["state", "lock", "disable"])
