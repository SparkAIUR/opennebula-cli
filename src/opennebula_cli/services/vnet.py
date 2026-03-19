"""Virtual network service."""

from __future__ import annotations

from opennebula_cli.sdk.models.common import ensure_list, object_get
from opennebula_cli.sdk.models.vnet import Vnet
from opennebula_cli.transports.base import OpenNebulaTransport


class VnetService:
    """Typed OpenNebula virtual network operations.

    Example:
        >>> service = VnetService(transport)
        >>> service.list()
        [Vnet(id=1, name='public', ...)]
    """

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self, *, filter_flag: int = -2, start_id: int = -1, end_id: int = -1) -> list[Vnet]:
        raw = self._transport.call("one.vnpool.info", filter_flag, start_id, end_id)
        items = ensure_list(object_get(raw, "VNET"))
        return [Vnet.from_raw(item) for item in items]

    def show(self, vnet_id: int) -> Vnet:
        raw = self._transport.call("one.vn.info", vnet_id, False)
        return Vnet.from_raw(raw)
