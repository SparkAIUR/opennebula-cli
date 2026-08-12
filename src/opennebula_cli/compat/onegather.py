"""Compatibility wrapper for onegather."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onegather compatibility wrapper."""

    run_compat("gather")
