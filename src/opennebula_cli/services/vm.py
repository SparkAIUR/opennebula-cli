"""VM service."""

from __future__ import annotations

import time

from opennebula_cli.sdk.exceptions import ApiError
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

    @staticmethod
    def _is_transient_poweroff_state(message: str) -> bool:
        return (
            'This action is not available for state' in message
            and any(state in message for state in ("PENDING", "PROLOG", "BOOT"))
        )

    def _poweroff_action(self, action: str, vm_id: int, *, retry_timeout: float) -> None:
        deadline = time.monotonic() + retry_timeout
        while True:
            try:
                self._transport.call("one.vm.action", action, vm_id)
                return
            except ApiError as exc:
                message = str(exc)
                if not self._is_transient_poweroff_state(message):
                    raise
                if time.monotonic() >= deadline:
                    raise
                time.sleep(3.0)

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
        self._poweroff_action(action, vm_id, retry_timeout=min(timeout if wait else 30.0, 60.0))
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
