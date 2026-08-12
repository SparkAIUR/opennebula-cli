"""Pre-I/O transport routing with an explicit no-replay contract."""

from __future__ import annotations

from typing import Any

from opennebula_cli.transports.pyone_adapter import PyoneTransport
from opennebula_cli.transports.xmlrpc_raw import RawXmlRpcTransport


class RoutingTransport:
    """Choose a backend from local binding capability before issuing a request."""

    def __init__(self, pyone: PyoneTransport, raw: RawXmlRpcTransport) -> None:
        self._pyone = pyone
        self._raw = raw
        self._last_backend: str | None = None

    @property
    def name(self) -> str:
        return "auto"

    @property
    def last_backend(self) -> str | None:
        return self._last_backend

    def supports(self, method: str) -> bool:
        return self._pyone.supports(method) or self._raw.supports(method)

    def call(self, method: str, *args: object) -> Any:
        selected = self._pyone if self._pyone.supports(method) else self._raw
        self._last_backend = selected.name
        # Deliberately no exception fallback: a submitted mutation must never replay.
        return selected.call(method, *args)
