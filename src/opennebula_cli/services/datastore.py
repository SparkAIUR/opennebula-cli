"""Datastore service."""

from __future__ import annotations

from opennebula_cli.sdk.models.common import ensure_list, object_get
from opennebula_cli.sdk.models.datastore import Datastore
from opennebula_cli.transports.base import OpenNebulaTransport


class DatastoreService:
    """Typed OpenNebula datastore operations.

    Example:
        >>> service = DatastoreService(transport)
        >>> service.show(3)
        Datastore(id=3, name='default', ...)
    """

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self) -> list[Datastore]:
        raw = self._transport.call("one.datastorepool.info")
        items = ensure_list(object_get(raw, "DATASTORE"))
        return [Datastore.from_raw(item) for item in items]

    def show(self, datastore_id: int) -> Datastore:
        raw = self._transport.call("one.datastore.info", datastore_id)
        return Datastore.from_raw(raw)
