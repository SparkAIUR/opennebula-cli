"""Renderer primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rich.console import Console

from opennebula_cli.sdk.models.common import normalize_value


@dataclass(slots=True)
class RenderContext:
    """Render-time context."""

    console: Console
    output: str
    interactive: bool
    no_pager: bool
    resource: str | None = None
    compact: bool = False
    no_header: bool = False
    official_schema: bool = False


def to_primitive(data: Any) -> Any:
    """Normalize renderer input to JSON-safe primitives."""

    return normalize_value(data)
