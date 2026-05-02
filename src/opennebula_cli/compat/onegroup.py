"""Compatibility wrapper for onegroup."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onegroup compatibility wrapper."""

    run_compat("group")
