"""Compatibility wrapper for onevrouter."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onevrouter compatibility wrapper."""

    run_compat("vrouter")
