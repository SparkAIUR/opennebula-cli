"""Compatibility wrapper for onehook."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onehook compatibility wrapper."""

    run_compat("hook")
