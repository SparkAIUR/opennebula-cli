"""Template service."""

from __future__ import annotations

import builtins
from typing import Any

from opennebula_cli.sdk.models.common import Ack, ensure_list, normalize_mapping, object_get
from opennebula_cli.sdk.models.template import Template
from opennebula_cli.services.official import run_official_command
from opennebula_cli.transports.base import OpenNebulaTransport


class TemplateService:
    """Typed VM template operations."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self) -> list[Template]:
        raw = self._transport.call("one.templatepool.info", -2, -1, -1)
        items = ensure_list(object_get(raw, "VMTEMPLATE"))
        return [Template.from_raw(item) for item in items]

    def show(self, template_id: int) -> Template:
        raw = self._transport.call("one.template.info", template_id)
        return Template.from_raw(raw)

    def show_full(self, template_id: int) -> dict[str, Any]:
        return normalize_mapping(self._transport.call("one.template.info", template_id))

    def delete(self, template_id: int) -> Ack:
        self._transport.call("one.template.delete", template_id, False)
        return Ack(resource="template", id=template_id, action="delete")

    def create(self, template_body: str) -> Ack:
        template_id = self._transport.call("one.template.allocate", template_body)
        return Ack(resource="template", id=int(template_id), action="create")

    def instantiate(
        self,
        template_id: int,
        *,
        name: str | None = None,
        template_body: str | None = None,
    ) -> Ack:
        vm_id = self._transport.call(
            "one.template.instantiate",
            template_id,
            name or "",
            False,
            template_body or "",
            False,
        )
        return Ack(resource="vm", id=int(vm_id), action="instantiate")

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        """Run a captured official template command not yet modeled by a typed method."""

        return run_official_command(self._transport, "template", verb, argv)
