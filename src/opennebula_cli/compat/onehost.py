"""Compatibility wrapper for onehost."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onehost compatibility wrapper."""

    run_compat("host")
