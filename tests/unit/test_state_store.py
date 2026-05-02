from __future__ import annotations

from pathlib import Path

from opennebula_cli.state_store import StateStore, StoredContext, default_state_db_path


def test_default_state_db_path_prefers_explicit_db(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "custom.db"
    monkeypatch.setenv("OPENNEBULA_CLI_STATE_DB", str(target))

    assert default_state_db_path() == target


def test_default_state_db_path_uses_state_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENNEBULA_CLI_STATE_DB", raising=False)
    monkeypatch.setenv("OPENNEBULA_CLI_STATE_DIR", str(tmp_path / "state-dir"))

    assert default_state_db_path() == (tmp_path / "state-dir" / "state.db")


def test_lock_round_trip_with_password(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")
    store.set_lock(actions={"all"}, commands={"vm"}, password="secret")

    state = store.lock_state()
    assert state.enabled is True
    assert state.actions == frozenset({"all"})
    assert state.commands == frozenset({"vm"})
    assert state.password_set is True
    assert store.verify_lock_password("secret") is True
    assert store.verify_lock_password("wrong") is False

    store.disable_lock()
    disabled = store.lock_state()
    assert disabled.enabled is False
    assert not disabled.actions
    assert not disabled.commands


def test_context_upsert_and_switch(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")
    store.upsert_context(
        StoredContext(
            name="staging",
            endpoint="https://staging.example.com/RPC2",
            username="user1",
            password="pass1",
            version="v7.0.2",
        )
    )
    store.upsert_context(
        StoredContext(
            name="production",
            endpoint="https://prod.example.com/RPC2",
            username="user2",
            password="pass2",
            version="v7.0.2",
        )
    )

    current = store.get_active_context()
    assert current is not None
    assert current.name == "production"

    assert store.use_context("staging") is True
    switched = store.get_active_context()
    assert switched is not None
    assert switched.name == "staging"
    assert switched.username == "user1"

    assert store.use_context("missing") is False
