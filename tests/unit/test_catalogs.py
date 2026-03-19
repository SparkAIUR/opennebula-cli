from __future__ import annotations

from pathlib import Path

from opennebula_cli.registry.catalog import load_catalogs


def test_wave_one_catalogs_load() -> None:
    catalogs = load_catalogs(Path("src/opennebula_cli/catalogs/v7_0/base"))
    assert {"vm", "host", "image", "template"} <= set(catalogs)
