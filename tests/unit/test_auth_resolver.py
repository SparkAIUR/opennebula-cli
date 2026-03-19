from __future__ import annotations

from pathlib import Path

import pytest

from opennebula_cli.auth.resolver import resolve_auth, resolve_auth_value
from opennebula_cli.sdk.exceptions import AuthError


def test_resolve_literal_auth_value() -> None:
    resolved = resolve_auth_value("alice:secret:token")
    assert resolved.username == "alice"
    assert resolved.secret == "secret:token"


def test_resolve_file_auth_value(tmp_path: Path) -> None:
    auth_file = tmp_path / "one_auth"
    auth_file.write_text("alice:secret\n", encoding="utf-8")
    resolved = resolve_auth_value(str(auth_file))
    assert resolved.raw_session == "alice:secret"


def test_malformed_auth_value_raises() -> None:
    with pytest.raises(AuthError):
        resolve_auth_value("missing-separator")


def test_resolve_auth_uses_default_file(tmp_path: Path) -> None:
    auth_file = tmp_path / "one_auth"
    auth_file.write_text("alice:secret\n", encoding="utf-8")
    resolved = resolve_auth(
        cli_auth=None,
        cli_user=None,
        cli_password=None,
        profile_auth=None,
        env_auth=None,
        default_auth_path=auth_file,
    )
    assert resolved.username == "alice"
