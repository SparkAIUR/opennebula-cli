"""Compatibility wrapper for onedb."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onedb compatibility wrapper."""

    run_compat("db")
