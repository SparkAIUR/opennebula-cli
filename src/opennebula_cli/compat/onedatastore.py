"""Compatibility wrapper for onedatastore."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onedatastore compatibility wrapper."""

    run_compat("datastore")
