"""Compatibility wrapper for onevmgroup."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onevmgroup compatibility wrapper."""

    run_compat("vmgroup")
