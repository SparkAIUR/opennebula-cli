"""Catalog loading."""

from __future__ import annotations

from pathlib import Path

import yaml

from opennebula_cli.registry.schema import FamilyCatalog


def load_catalog(path: Path) -> FamilyCatalog:
    """Load a single YAML catalog file."""

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return FamilyCatalog.model_validate(data)


def load_catalogs(root: Path) -> dict[str, FamilyCatalog]:
    """Load all catalogs under a directory."""

    catalogs: dict[str, FamilyCatalog] = {}
    for path in sorted(root.glob("*.yaml")):
        if path.name == "shared.yaml":
            continue
        catalog = load_catalog(path)
        catalogs[catalog.family] = catalog
    return catalogs
