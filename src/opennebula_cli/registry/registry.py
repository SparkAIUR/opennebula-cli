"""In-memory registry helpers."""

from __future__ import annotations

from pathlib import Path

from opennebula_cli.registry.catalog import load_catalogs
from opennebula_cli.registry.schema import FamilyCatalog


class CommandRegistry:
    """Versioned registry of command metadata."""

    def __init__(self, catalogs: dict[str, FamilyCatalog]) -> None:
        self._catalogs = catalogs

    @classmethod
    def from_repo(cls, root: Path) -> CommandRegistry:
        return cls(load_catalogs(root))

    def families(self) -> list[str]:
        return sorted(self._catalogs)

    def family(self, name: str) -> FamilyCatalog:
        return self._catalogs[name]
