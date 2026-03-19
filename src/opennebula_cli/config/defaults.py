"""Default path helpers."""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_config_dir


def default_auth_path() -> Path:
    """Return the default OpenNebula auth path."""

    return Path.home() / ".one" / "one_auth"


def default_config_path() -> Path:
    """Return the default config TOML path."""

    return Path(user_config_dir("opennebula-cli", "SparkAIUR")) / "config.toml"
