"""Transport protocols."""

from __future__ import annotations

from typing import Any, Protocol


class OpenNebulaTransport(Protocol):
    """Common transport interface for XML-RPC backends."""

    def call(self, method: str, *args: object) -> Any:
        """Invoke an OpenNebula backend method."""

    def supports(self, method: str) -> bool:
        """Return whether the method can be routed without performing I/O."""

    @property
    def name(self) -> str:
        """Stable transport identifier for results and errors."""


class PluginTransport(Protocol):
    """REST-ish transport for plugins."""

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json: dict[str, object] | None = None,
    ) -> Any:
        """Issue a plugin backend request."""
