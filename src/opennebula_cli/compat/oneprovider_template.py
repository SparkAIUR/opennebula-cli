"""Guarded-preview compatibility wrapper for oneprovider-template."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    run_compat("provider-template")
