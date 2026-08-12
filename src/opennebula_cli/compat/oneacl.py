"""Compatibility wrapper for oneacl."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the oneacl compatibility wrapper."""

    run_compat("acl")
