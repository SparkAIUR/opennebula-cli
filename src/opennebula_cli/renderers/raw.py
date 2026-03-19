"""Raw text renderer."""

from __future__ import annotations

from typing import Any

from opennebula_cli.renderers.base import RenderContext, to_primitive


def render_raw(data: Any, *, ctx: RenderContext) -> None:
    """Render plain raw-ish output."""

    primitive = to_primitive(data)
    ctx.console.print(str(primitive))
