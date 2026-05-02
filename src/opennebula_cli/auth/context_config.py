"""Auth context config loading from OPENNEBULA_CLI_AUTH_CONFIG."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True, frozen=True)
class FileContextAuth:
    """Credential payload for a context."""

    username: str
    password: str


@dataclass(slots=True, frozen=True)
class FileContext:
    """Context entry from auth.yaml."""

    name: str
    endpoint: str
    auth: FileContextAuth
    version: str | None = None
    endpoints: dict[str, str] | None = None
    config: dict[str, str] | None = None


@dataclass(slots=True, frozen=True)
class AuthConfigFile:
    """Loaded auth configuration content."""

    current_context: str
    contexts: tuple[FileContext, ...]

    def resolve_current(self) -> FileContext | None:
        for context in self.contexts:
            if context.name == self.current_context:
                return context
        return None


def auth_config_path() -> Path:
    """Resolve auth config path from env and defaults."""

    explicit = os.getenv("OPENNEBULA_CLI_AUTH_CONFIG")
    if explicit:
        return Path(explicit).expanduser()

    xdg_home = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    return xdg_home / "opennebula-cli" / "auth.yaml"


def load_auth_config() -> AuthConfigFile | None:
    """Load auth config if present and valid enough for runtime use."""

    target = auth_config_path()
    if not target.exists() or not target.is_file():
        return None

    raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None

    current_context_raw = raw.get("current_context")
    contexts_raw = raw.get("contexts")
    if not isinstance(current_context_raw, str) or not isinstance(contexts_raw, list):
        return None

    contexts: list[FileContext] = []
    for item in contexts_raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        endpoint = item.get("endpoint")
        auth = item.get("auth")
        if not isinstance(name, str) or not isinstance(endpoint, str) or not isinstance(auth, dict):
            continue
        username = auth.get("username")
        password = auth.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            continue
        version_raw = item.get("version")
        endpoints_raw = item.get("endpoints")
        config_raw = item.get("config")
        parsed_endpoints: dict[str, str] | None = None
        parsed_config: dict[str, str] | None = None
        if isinstance(endpoints_raw, dict):
            parsed_endpoints = {
                str(key): str(value)
                for key, value in endpoints_raw.items()
                if isinstance(key, str) and isinstance(value, str)
            }
        if isinstance(config_raw, dict):
            parsed_config = {
                str(key): str(value)
                for key, value in config_raw.items()
                if isinstance(key, str) and isinstance(value, (str, int, float, bool))
            }
        contexts.append(
            FileContext(
                name=name,
                endpoint=endpoint,
                auth=FileContextAuth(username=username, password=password),
                version=str(version_raw) if isinstance(version_raw, str) else None,
                endpoints=parsed_endpoints,
                config=parsed_config,
            )
        )

    return AuthConfigFile(current_context=str(current_context_raw), contexts=tuple(contexts))
