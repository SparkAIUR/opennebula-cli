"""Database tooling service."""

from __future__ import annotations

import builtins

from opennebula_cli.services.placeholder import run_placeholder_official


class DbService:
    """Placeholder onedb operations."""

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        return run_placeholder_official("db", verb, argv)
