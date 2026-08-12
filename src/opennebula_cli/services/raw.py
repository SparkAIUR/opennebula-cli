"""Guarded raw XML-RPC service."""

from __future__ import annotations

from typing import Any

from opennebula_cli.sdk.models.common import normalize_value
from opennebula_cli.sdk.models.raw import RawCallResult
from opennebula_cli.transports.base import OpenNebulaTransport


class RawService:
    """Explicit raw XML-RPC escape hatch."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def call(self, method: str, args: list[Any]) -> RawCallResult:
        """Invoke an arbitrary XML-RPC method."""

        raw_call = getattr(self._transport, "call_raw", None)
        result = (
            raw_call(method, *args) if callable(raw_call) else self._transport.call(method, *args)
        )
        transport_name = getattr(self._transport, "name", "unknown")
        return RawCallResult(
            method=method,
            transport=transport_name,
            result=normalize_value(result),
        )
