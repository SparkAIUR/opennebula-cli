"""Validate repository catalog files."""

from __future__ import annotations

from pathlib import Path

from opennebula_cli.registry.catalog import load_catalogs


def main() -> None:
    """Load and validate all tracked family catalogs."""
    root = Path("src/opennebula_cli/catalogs/v7_0/base")
    catalogs = load_catalogs(root)
    for family, catalog in sorted(catalogs.items()):
        print(f"{family}: {len(catalog.commands)} commands")


if __name__ == "__main__":
    main()
