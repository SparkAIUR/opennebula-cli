"""Compatibility wrapper for onecluster."""

from opennebula_cli.compat.common import run_compat


def main() -> None:
    """Run the onecluster compatibility wrapper."""

    run_compat("cluster")
