"""Compatibility wrapper for oneacct."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the oneacct compatibility wrapper."""

    run_compat("acct")
