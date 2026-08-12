"""Guarded-preview compatibility wrapper for oneprovision-template."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    run_compat("provision-template")
