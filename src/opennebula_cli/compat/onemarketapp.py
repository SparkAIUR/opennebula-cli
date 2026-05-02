"""Compatibility wrapper for onemarketapp."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onemarketapp compatibility wrapper."""

    run_compat("marketapp")
