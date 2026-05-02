"""Compatibility wrapper for onegate."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onegate compatibility wrapper."""

    run_compat("gate")
