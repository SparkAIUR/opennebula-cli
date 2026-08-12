"""Compatibility wrapper for oneuser."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the oneuser compatibility wrapper."""

    run_compat("user")
