"""Vntemplate service."""

from __future__ import annotations

import builtins

from opennebula_cli.services.placeholder import run_placeholder_official
from opennebula_cli.transports.base import OpenNebulaTransport


class VntemplateService:
    """Placeholder vntemplate operations."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        return run_placeholder_official("vntemplate", verb, argv)
