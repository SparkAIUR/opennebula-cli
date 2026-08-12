"""Catalog schema models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CommandParity(BaseModel):
    """Parity metadata for a command."""

    model_config = ConfigDict(frozen=True)

    status: Literal[
        "not_started",
        "cataloged",
        "scaffolded",
        "implemented",
        "tested_unit",
        "tested_contract",
        "parity_verified",
        "deferred",
        "intentionally_divergent",
    ] = "cataloged"
    source: str = "official-cli"
    notes: str | None = None


class CommandDefinition(BaseModel):
    """Single command definition."""

    model_config = ConfigDict(frozen=True)

    aliases: list[str] = Field(default_factory=list)
    handler: Literal["rpc", "composite", "rest"]
    backend_method: str | None = None
    supports_wait: bool = False
    outputs: list[str] = Field(
        default_factory=lambda: ["table", "json", "yaml", "xml", "csv", "raw"]
    )
    args: list[dict[str, object]] = Field(default_factory=list)
    options: list[dict[str, object]] = Field(default_factory=list)
    parity: CommandParity = Field(default_factory=CommandParity)


class FamilyCatalog(BaseModel):
    """Catalog file for a command family."""

    model_config = ConfigDict(frozen=True)

    family: str
    script: str
    version: str
    commands: dict[str, CommandDefinition]


class MethodSignature(BaseModel):
    """Versioned API method metadata used for routing and safety decisions."""

    model_config = ConfigDict(frozen=True)

    arguments: list[str] = Field(default_factory=list)
    transport: Literal["xmlrpc", "rest", "composite", "local"] = "xmlrpc"
    safety: Literal["read", "mutation", "unknown"] = "unknown"
    idempotency: Literal["safe", "idempotent", "non_idempotent", "unknown"] = "unknown"
    preview: bool = False
    notes: str | None = None


class VersionProfileCatalog(BaseModel):
    """Complete command and capability inventory for one server line."""

    model_config = ConfigDict(frozen=True)

    profile: Literal["7.0", "7.4"]
    server_line: str
    commands: dict[str, list[str]]
    methods: dict[str, MethodSignature] = Field(default_factory=dict)
