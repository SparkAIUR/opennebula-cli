"""Compatibility wrapper for onevm."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onevm compatibility wrapper."""

    run_compat("vm")
