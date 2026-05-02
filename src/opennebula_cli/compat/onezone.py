"""Compatibility wrapper for onezone."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onezone compatibility wrapper."""

    run_compat("zone")
