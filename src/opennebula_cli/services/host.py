"""Host service."""

from __future__ import annotations

import builtins
from typing import Any

from opennebula_cli.sdk.models.common import Ack, ensure_list, normalize_mapping, object_get
from opennebula_cli.sdk.models.host import Host
from opennebula_cli.services.official import run_official_command
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

    def show_full(self, host_id: int) -> dict[str, Any]:
        return normalize_mapping(self._transport.call("one.host.info", host_id))

    def flush(self, host_id: int, *, delete_recreate: bool = False) -> builtins.list[Ack]:
        """Disable a host and reschedule its VMs using the official composite workflow."""

        self._transport.call("one.host.status", host_id, 1)
        raw = self._transport.call("one.vmpool.infoextended", -2, -1, -1, -1)
        results = [Ack(resource="host", id=host_id, action="disable")]
        for vm in ensure_list(object_get(raw, "VM")):
            history = ensure_list(object_get(object_get(vm, "HISTORY_RECORDS", {}), "HISTORY"))
            latest = history[-1] if history else None
            if latest is None or int(object_get(latest, "HID", -1)) != host_id:
                continue
            vm_id = int(object_get(vm, "ID"))
            if delete_recreate:
                self._transport.call("one.vm.recover", vm_id, 4)
                action = "recover-delete-recreate"
            else:
                self._transport.call("one.vm.action", "resched", vm_id)
                action = "resched"
            results.append(Ack(resource="vm", id=vm_id, action=action))
        return results

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        """Run a captured official host command not yet modeled by a typed method."""

        return run_official_command(self._transport, "host", verb, argv)
