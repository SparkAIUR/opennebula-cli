"""Compatibility wrapper for onevntemplate."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onevntemplate compatibility wrapper."""

    run_compat("vntemplate")
