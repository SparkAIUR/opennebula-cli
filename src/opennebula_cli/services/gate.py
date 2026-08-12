"""OneGate compatibility service."""

from __future__ import annotations

import builtins

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.sdk.models.common import Ack, normalize_value
from opennebula_cli.services.official import parse_official_args, require_positionals
from opennebula_cli.transports.base import OpenNebulaTransport


class OneGateService:
    """Compatibility service for captured onegate commands."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        parsed = parse_official_args(argv)

        if verb == "vm-show":
            vm_id = int(require_positionals(parsed, 1, "vm-show <vmid>")[0])
            return normalize_value(self._transport.call("one.vm.info", vm_id))
        if verb == "vm-update":
            positionals = require_positionals(parsed, 1, "vm-update <vmid>")
            vm_id = int(positionals[0])
            lines: list[str] = []
            data = parsed.options.get("data")
            if data:
                lines.extend(str(data).split("\n"))
            erase = parsed.options.get("erase")
            if erase:
                lines.append(f'{erase} = ""')
            template_text = "\n".join(line for line in lines if line.strip())
            self._transport.call("one.vm.update", vm_id, template_text, True)
            return Ack(resource="vm", id=vm_id, action=verb)
        if verb in {
            "resume",
            "stop",
            "suspend",
            "terminate",
            "reboot",
            "poweroff",
            "resched",
            "unresched",
            "hold",
            "release",
        }:
            vm_id = int(require_positionals(parsed, 1, f"{verb} <vmid>")[0])
            action = verb
            if verb in {"terminate", "reboot", "poweroff"} and "hard" in parsed.flags:
                action = f"{verb}-hard"
            self._transport.call("one.vm.action", action, vm_id)
            return Ack(resource="vm", id=vm_id, action=verb)
        if verb == "service-show":
            service_id = int(require_positionals(parsed, 1, "service-show <serviceid>")[0])
            return {
                "resource": "service",
                "id": service_id,
                "action": verb,
                "message": "Use 'flow show' for full service details",
            }
        if verb == "service-scale":
            service_id = int(require_positionals(parsed, 1, "service-scale <serviceid>")[0])
            return Ack(resource="service", id=service_id, action=verb)
        if verb == "vrouter-show":
            vrouter_id = int(require_positionals(parsed, 1, "vrouter-show <vrouterid>")[0])
            return normalize_value(self._transport.call("one.vrouter.info", vrouter_id))
        if verb == "vnet-show":
            vnet_id = int(require_positionals(parsed, 1, "vnet-show <vnetid>")[0])
            return normalize_value(self._transport.call("one.vn.info", vnet_id))

        raise ApiError(f"Unsupported gate command: {verb}")
