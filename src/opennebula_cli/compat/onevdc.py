"""Compatibility wrapper for onevdc."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onevdc compatibility wrapper."""

    run_compat("vdc")
