"""Compatibility wrapper for oneswap."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the oneswap compatibility wrapper."""

    run_compat("swap")
