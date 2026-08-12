"""Resolve OpenNebula auth input from CLI, profiles, and environment."""

from __future__ import annotations

from getpass import getpass
from pathlib import Path

from opennebula_cli.auth.models import ResolvedAuth
from opennebula_cli.sdk.exceptions import AuthError


def _split_session(value: str, *, source: str) -> ResolvedAuth:
    session = value.strip()
    username, separator, secret = session.partition(":")
    if not separator or not username:
        raise AuthError(f"Malformed auth value from {source}. Expected 'user:secret'.")
    return ResolvedAuth(
        username=username,
        secret=secret,
        source=source,
        raw_session=f"{username}:{secret}",
    )


def _read_auth_file(path: Path) -> ResolvedAuth:
    if not path.exists():
        raise AuthError(f"Auth file does not exist: {path}")
    if not path.is_file():
        raise AuthError(f"Auth path is not a file: {path}")
    line = ""
    for candidate in path.read_text(encoding="utf-8").splitlines():
        if candidate.strip():
            line = candidate
            break
    if not line.strip():
        raise AuthError(f"Auth file is empty: {path}")
    return _split_session(line, source=f"file:{path}")


def resolve_auth_value(value: str) -> ResolvedAuth:
    """Resolve a literal or file-based auth value."""

    if value.startswith("file:"):
        return _read_auth_file(Path(value[5:]).expanduser())
    if value.startswith("literal:"):
        return _split_session(value[8:], source="literal")
    expanded = Path(value).expanduser()
    if expanded.exists():
        return _read_auth_file(expanded)
    return _split_session(value, source="literal-auto")


def resolve_auth(
    *,
    cli_auth: str | None,
    cli_user: str | None,
    cli_password: str | None,
    profile_auth: str | None,
    context_auth: str | None = None,
    context_source: str | None = None,
    env_auth: str | None,
    default_auth_path: Path,
) -> ResolvedAuth:
    """Resolve auth using the project precedence rules."""

    if cli_user:
        password = cli_password or getpass(f"Password for {cli_user}: ")
        return _split_session(f"{cli_user}:{password}", source="cli-user")
    if cli_auth:
        return resolve_auth_value(cli_auth)
    if profile_auth:
        return resolve_auth_value(profile_auth)
    if context_auth:
        resolved = resolve_auth_value(context_auth)
        if context_source is None:
            return resolved
        return ResolvedAuth(
            username=resolved.username,
            secret=resolved.secret,
            source=context_source,
            raw_session=resolved.raw_session,
        )
    if env_auth:
        return resolve_auth_value(env_auth)
    return _read_auth_file(default_auth_path.expanduser())
