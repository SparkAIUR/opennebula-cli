"""Compatibility wrapper for oneimage."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the oneimage compatibility wrapper."""

    run_compat("image")
