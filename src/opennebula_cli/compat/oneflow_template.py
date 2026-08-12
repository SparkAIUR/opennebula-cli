"""Compatibility wrapper for oneflow-template."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the oneflow-template compatibility wrapper."""

    run_compat("flow-template")
