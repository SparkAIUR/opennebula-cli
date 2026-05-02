"""Compatibility wrapper for onemarket."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onemarket compatibility wrapper."""

    run_compat("market")
