"""Compatibility wrapper for oneform."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    run_compat("form")
