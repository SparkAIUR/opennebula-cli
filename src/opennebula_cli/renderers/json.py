"""JSON renderer."""

from __future__ import annotations

import json
from typing import Any

from opennebula_cli.renderers.base import RenderContext, to_primitive


def render_json(data: Any, *, ctx: RenderContext) -> None:
    """Render JSON output."""

    indent = None if ctx.compact else 2
    separators = (",", ":") if ctx.compact else None
    payload = json.dumps(to_primitive(data), indent=indent, sort_keys=True, separators=separators)
    ctx.console.file.write(f"{payload}\n")
