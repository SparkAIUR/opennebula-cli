"""VM service."""

from __future__ import annotations

from opennebula_cli.sdk.models.common import Ack, WaitResult, ensure_list, object_get
from opennebula_cli.sdk.models.vm import Vm
from opennebula_cli.transports.base import OpenNebulaTransport
from opennebula_cli.waiters.generic import wait_for
from opennebula_cli.waiters.vm import is_powered_off


class VmService:
    """Typed VM operations."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self, *, filter_flag: int = -2, state: int = -1) -> list[Vm]:
        raw = self._transport.call("one.vmpool.infoextended", filter_flag, -1, -1, state)
        items = ensure_list(object_get(raw, "VM"))
        return [Vm.from_raw(item) for item in items]

    def show(self, vm_id: int) -> Vm:
        raw = self._transport.call("one.vm.info", vm_id)
        return Vm.from_raw(raw)

    def poweroff(
        self,
        vm_id: int,
        *,
        hard: bool = False,
        wait: bool = False,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
        show_progress: bool = True,
    ) -> Ack | WaitResult:
        action = "poweroff-hard" if hard else "poweroff"
        self._transport.call("one.vm.action", action, vm_id)
        if not wait:
            return Ack(resource="vm", id=vm_id, action=action)
        return wait_for(
            resource="vm",
            resource_id=vm_id,
            fetch=lambda: self.show(vm_id),
            predicate=is_powered_off,
            state_label=lambda vm: f"{vm.state}/{vm.lcm_state or '-'}",
            timeout=timeout,
            poll_interval=poll_interval,
            show_progress=show_progress,
        )
