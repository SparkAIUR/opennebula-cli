"""JSON renderer."""

from __future__ import annotations

import json
from typing import Any

from opennebula_cli.renderers.base import RenderContext, to_primitive


def render_json(data: Any, *, ctx: RenderContext) -> None:
    """Render JSON output."""

    payload = json.dumps(to_primitive(data), indent=2, sort_keys=True)
    ctx.console.file.write(f"{payload}\n")
