"""Compatibility wrapper for oneshowback."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the oneshowback compatibility wrapper."""

    run_compat("showback")
