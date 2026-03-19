"""Compatibility wrapper for onevnet."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onevnet compatibility wrapper."""

    run_compat("vnet")
