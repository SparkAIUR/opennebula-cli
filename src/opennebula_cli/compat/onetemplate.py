"""Compatibility wrapper for onetemplate."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onetemplate compatibility wrapper."""

    run_compat("template")
