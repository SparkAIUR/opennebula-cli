"""Compatibility wrapper for onecfg."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onecfg compatibility wrapper."""

    run_compat("cfg")
