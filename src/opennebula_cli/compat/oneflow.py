"""Compatibility wrapper for oneflow."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the oneflow compatibility wrapper."""

    run_compat("flow")
