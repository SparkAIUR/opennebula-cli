"""Compatibility wrapper for onesecgroup."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onesecgroup compatibility wrapper."""

    run_compat("secgroup")
