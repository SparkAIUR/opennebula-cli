"""Server-version and negotiated capability models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CapabilityProfile(BaseModel):
    """Effective compatibility profile selected for a connected server."""

    model_config = ConfigDict(frozen=True)

    name: Literal["7.0", "7.4"]
    server_version: str
    methods: frozenset[str] = Field(default_factory=frozenset)
    services: frozenset[str] = Field(default_factory=lambda: frozenset({"xmlrpc"}))

    def supports(self, capability: str) -> bool:
        return capability in self.methods or capability in self.services


class ServerInfo(BaseModel):
    """Authenticated identity and compatibility metadata for one endpoint."""

    model_config = ConfigDict(frozen=True)

    version: str
    profile: Literal["7.0", "7.4"]
    endpoint: str
    username: str
    transport: str
