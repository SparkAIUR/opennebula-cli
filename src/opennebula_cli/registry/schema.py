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
