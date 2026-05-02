"""Compatibility wrapper for onelog."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onelog compatibility wrapper."""

    run_compat("log")
