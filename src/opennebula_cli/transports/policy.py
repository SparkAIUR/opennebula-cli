"""Fail-closed context policy wrapper for all XML-RPC SDK surfaces."""

from __future__ import annotations

from opennebula_cli.sdk.exceptions import PolicyError
from opennebula_cli.transports.base import OpenNebulaTransport


def is_read_only_method(method: str) -> bool:
    """Classify known read-only XML-RPC methods conservatively."""

    return method == "one.system.version" or method.endswith(
        (".info", ".infoextended", ".monitoring")
    )


class PolicyTransport:
    """Deny every non-read operation before it reaches the selected backend."""

    name = "policy"

    def __init__(self, transport: OpenNebulaTransport, *, context: str | None) -> None:
        self._transport = transport
        self._context = context

    @property
    def last_backend(self) -> str | None:
        return getattr(self._transport, "last_backend", None)

    def supports(self, method: str) -> bool:
        return self._transport.supports(method)

    def call(self, method: str, *args: object) -> object:
        if not is_read_only_method(method):
            raise PolicyError(
                f"Context '{self._context or '<none>'}' denies mutating method {method}.",
                method=method,
                context=self._context,
            )
        return self._transport.call(method, *args)

    def call_raw(self, method: str, *args: object) -> object:
        """Preserve literal read payloads without weakening mutation policy."""

        if not is_read_only_method(method):
            raise PolicyError(
                f"Context '{self._context or '<none>'}' denies mutating method {method}.",
                method=method,
                context=self._context,
            )
        raw_call = getattr(self._transport, "call_raw", None)
        if raw_call is not None:
            return raw_call(method, *args)
        return self._transport.call(method, *args)
