"""VM service."""

from __future__ import annotations

import builtins
import time
from typing import Any, Literal

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.sdk.models.common import (
    Ack,
    WaitResult,
    ensure_list,
    normalize_mapping,
    object_get,
)
from opennebula_cli.sdk.models.vm import Vm, VmDisk
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

    def show_full(self, vm_id: int) -> dict[str, Any]:
        """Return normalized raw VM data without dropping OpenNebula fields."""

        raw = self._transport.call("one.vm.info", vm_id)
        return normalize_mapping(raw)

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _disk_from_raw(cls, raw: object) -> VmDisk:
        normalized = normalize_mapping(raw)
        image = normalized.get("IMAGE")
        target = normalized.get("TARGET")
        source = normalized.get("SOURCE")
        serial = normalized.get("SERIAL")
        return VmDisk(
            disk_id=cls._int_or_none(normalized.get("DISK_ID")),
            image_id=cls._int_or_none(normalized.get("IMAGE_ID")),
            image=str(image) if image not in (None, "") else None,
            target=str(target) if target not in (None, "") else None,
            dev_prefix=(
                str(normalized["DEV_PREFIX"])
                if normalized.get("DEV_PREFIX") not in (None, "")
                else None
            ),
            datastore_id=cls._int_or_none(normalized.get("DATASTORE_ID")),
            source=str(source) if source not in (None, "") else None,
            serial=str(serial) if serial not in (None, "") else None,
            raw=normalized,
        )

    def disk_list(self, vm_id: int) -> builtins.list[VmDisk]:
        """List VM disks with IDs and target details needed for recovery."""

        full = self.show_full(vm_id)
        template = full.get("TEMPLATE", {})
        disks: object = None
        if isinstance(template, dict):
            disks = template.get("DISK")
        return [self._disk_from_raw(disk) for disk in ensure_list(disks)]

    @staticmethod
    def _quote_template_value(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def disk_attach(
        self,
        vm_id: int,
        *,
        image_id: int,
        dev_prefix: str | None = None,
        target: str | None = None,
        driver: str | None = None,
        cache: str | None = None,
        readonly: bool = False,
    ) -> Ack:
        """Attach an image as a disk."""

        attrs = [("IMAGE_ID", str(image_id))]
        if dev_prefix:
            attrs.append(("DEV_PREFIX", dev_prefix))
        if target:
            attrs.append(("TARGET", target))
        if driver:
            attrs.append(("DRIVER", driver))
        if cache:
            attrs.append(("CACHE", cache))
        if readonly:
            attrs.append(("READONLY", "YES"))
        body = ", ".join(f"{key} = {self._quote_template_value(value)}" for key, value in attrs)
        self._transport.call("one.vm.attach", vm_id, f"DISK = [ {body} ]")
        return Ack(resource="vm", id=vm_id, action="disk-attach")

    def disk_detach(self, vm_id: int, *, disk_id: int) -> Ack:
        """Detach a disk from a VM."""

        self._transport.call("one.vm.detach", vm_id, disk_id)
        return Ack(resource="vm", id=vm_id, action="disk-detach")

    def action(self, vm_id: int, action: str) -> Ack:
        """Run a VM lifecycle action."""

        self._transport.call("one.vm.action", action, vm_id)
        return Ack(resource="vm", id=vm_id, action=action)

    def recover(
        self,
        vm_id: int,
        operation: Literal["failure", "success", "retry", "delete"],
    ) -> Ack:
        """Recover a VM with the selected OpenNebula recovery operation."""

        operations = {
            "failure": 0,
            "success": 1,
            "retry": 2,
            "delete": 3,
        }
        self._transport.call("one.vm.recover", vm_id, operations[operation])
        return Ack(resource="vm", id=vm_id, action=f"recover-{operation}")

    def wait_state(
        self,
        vm_id: int,
        *,
        state: str,
        lcm_state: str | None = None,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
        show_progress: bool = True,
    ) -> WaitResult:
        """Wait for a VM state and optional LCM state."""

        expected_state = state.upper()
        expected_lcm_state = lcm_state.upper() if lcm_state else None

        def predicate(vm: Vm) -> bool:
            actual_state = vm.state.upper()
            actual_lcm_state = vm.lcm_state.upper() if vm.lcm_state else None
            return actual_state == expected_state and (
                expected_lcm_state is None or actual_lcm_state == expected_lcm_state
            )

        return wait_for(
            resource="vm",
            resource_id=vm_id,
            fetch=lambda: self.show(vm_id),
            predicate=predicate,
            state_label=lambda vm: f"{vm.state}/{vm.lcm_state or '-'}",
            timeout=timeout,
            poll_interval=poll_interval,
            show_progress=show_progress,
        )

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
