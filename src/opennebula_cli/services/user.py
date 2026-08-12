"""User service."""

from __future__ import annotations

import builtins

from opennebula_cli.sdk.models.common import ensure_list, object_get
from opennebula_cli.sdk.models.user import User
from opennebula_cli.services.official import run_official_command
from opennebula_cli.transports.base import OpenNebulaTransport


class UserService:
    """Typed user operations."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self) -> list[User]:
        raw = self._transport.call("one.userpool.info", -2, -1, -1)
        items = ensure_list(object_get(raw, "USER"))
        return [User.from_raw(item) for item in items]

    def show(self, user_id: int) -> User:
        raw = self._transport.call("one.user.info", user_id)
        return User.from_raw(raw)

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        """Run a captured official user command not yet modeled by a typed method."""

        return run_official_command(self._transport, "user", verb, argv)
