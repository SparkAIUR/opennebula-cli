"""ACL service."""

from __future__ import annotations

import builtins

from opennebula_cli.sdk.models.acl import AclRule
from opennebula_cli.sdk.models.common import ensure_list, object_get
from opennebula_cli.services.official import run_official_command
from opennebula_cli.transports.base import OpenNebulaTransport


class AclService:
    """Typed ACL operations."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self) -> list[AclRule]:
        raw = self._transport.call("one.aclpool.info")
        items = ensure_list(object_get(raw, "ACL"))
        return [AclRule.from_raw(item) for item in items]

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        """Run a captured official ACL command not yet modeled by a typed method."""

        return run_official_command(self._transport, "acl", verb, argv)
