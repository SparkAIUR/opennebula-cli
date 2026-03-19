"""Profile file loading."""

from __future__ import annotations

import tomllib
from pathlib import Path

from opennebula_cli.config.models import ConfigFile


def load_config_file(path: Path | None) -> ConfigFile:
    """Load a config file if it exists."""

    target = path
    if target is None or not target.exists():
        return ConfigFile()
    data = tomllib.loads(target.read_text(encoding="utf-8"))
    return ConfigFile.model_validate(data)
