"""Host service."""

from __future__ import annotations

from opennebula_cli.sdk.models.common import Ack, ensure_list, object_get
from opennebula_cli.sdk.models.host import Host
from opennebula_cli.transports.base import OpenNebulaTransport


class HostService:
    """Typed host operations."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self) -> list[Host]:
        raw = self._transport.call("one.hostpool.info")
        items = ensure_list(object_get(raw, "HOST"))
        return [Host.from_raw(item) for item in items]

    def show(self, host_id: int) -> Host:
        raw = self._transport.call("one.host.info", host_id)
        return Host.from_raw(raw)

    def flush(self, host_id: int) -> Ack:
        self._transport.call("one.host.flush", host_id)
        return Ack(resource="host", id=host_id, action="flush")
