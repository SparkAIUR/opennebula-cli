"""Plugin interfaces."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class PluginSpec(BaseModel):
    """Metadata returned by plugins."""

    model_config = ConfigDict(frozen=True)

    name: str
    plugin_api_version: str = "1"
    supported_opennebula: str = "7.4.x"
    commands: list[str] = Field(default_factory=list)


class Plugin(Protocol):
    """Minimal plugin contract."""

    def spec(self) -> PluginSpec:
        """Return plugin metadata."""

    def register(self) -> dict[str, Callable[..., object]]:
        """Return registrations."""
