"""Emit a simple parity inventory report from the catalogs."""

from __future__ import annotations

from pathlib import Path

from opennebula_cli.registry.registry import CommandRegistry


def main() -> None:
    """Print the current family.command -> parity status map."""
    registry = CommandRegistry.from_repo(Path("src/opennebula_cli/catalogs/v7_0/base"))
    for family in registry.families():
        catalog = registry.family(family)
        for command_name, definition in sorted(catalog.commands.items()):
            print(f"{family}.{command_name}: {definition.parity.status}")


if __name__ == "__main__":
    main()
