"""Group service."""

from __future__ import annotations

import builtins

from opennebula_cli.sdk.models.common import Ack, ensure_list, object_get
from opennebula_cli.sdk.models.group import Group
from opennebula_cli.services.official import run_official_command
from opennebula_cli.transports.base import OpenNebulaTransport


class GroupService:
    """Typed group operations."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self) -> list[Group]:
        raw = self._transport.call("one.grouppool.info", -2, -1, -1)
        items = ensure_list(object_get(raw, "GROUP"))
        return [Group.from_raw(item) for item in items]

    def show(self, group_id: int) -> Group:
        raw = self._transport.call("one.group.info", group_id)
        return Group.from_raw(raw)

    def set_vlan(self, group_id: int, vlan_rules: str) -> Ack:
        self._transport.call("one.group.vlan", group_id, vlan_rules)
        return Ack(resource="group", id=group_id, action="vlan")

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        """Run a captured official group command not yet modeled by a typed method."""

        return run_official_command(self._transport, "group", verb, argv)
