"""Compatibility entrypoint helpers."""

from __future__ import annotations

import sys

from opennebula_cli.cli.app import app


def run_compat(resource: str) -> None:
    """Rewrite argv to the canonical form and execute the Typer app."""

    sys.argv = ["one", resource, *sys.argv[1:]]
    app()
