"""Configuration models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.auth.models import ResolvedAuth

OutputMode = Literal["table", "json", "yaml", "xml", "csv", "raw", "human", "plain"]

CANONICAL_OUTPUT_MODES = ("table", "json", "yaml", "xml", "csv", "raw")
EXTENDED_OUTPUT_MODES = ("human", "plain")
ALL_OUTPUT_MODES = (*CANONICAL_OUTPUT_MODES, *EXTENDED_OUTPUT_MODES)
CANONICAL_OUTPUT_MODE_HELP = "|".join(CANONICAL_OUTPUT_MODES)


class ConnectionSettings(BaseModel):
    """Transport-specific connection configuration."""

    model_config = ConfigDict(frozen=True)

    endpoint: str
    timeout: float = 60.0
    verify_ssl: bool = True
    cert_dir: str | None = None
    service_endpoints: dict[str, str] = Field(default_factory=dict)
    service_config: dict[str, str] = Field(default_factory=dict)


class OutputSettings(BaseModel):
    """Renderer and paging configuration."""

    model_config = ConfigDict(frozen=True)

    output: OutputMode = "table"
    no_pager: bool = False
    pager: str | None = None
    listconf: str | None = None
    pool_page_size: int | None = None


class ProfileConfig(BaseModel):
    """Named profile configuration from TOML."""

    endpoint: str | None = None
    auth: str | None = None
    output: OutputMode | None = None
    timeout: float | None = None
    verify_ssl: bool | None = None
    cert_dir: str | None = None
    no_pager: bool | None = None


class ConfigFile(BaseModel):
    """Top-level config file shape."""

    default_profile: str | None = None
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)
    views: dict[str, str] = Field(default_factory=dict)
    plugins: dict[str, dict[str, str]] = Field(default_factory=dict)


class ResolvedConfig(BaseModel):
    """Fully merged runtime configuration."""

    model_config = ConfigDict(frozen=True)

    profile: str | None = None
    connection: ConnectionSettings
    auth: ResolvedAuth
    output: OutputSettings = Field(default_factory=OutputSettings)
    verbose: int = 0
    debug: bool = False
