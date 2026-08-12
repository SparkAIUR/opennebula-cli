"""Raw text renderer."""

from __future__ import annotations

import json
from typing import Any

from opennebula_cli.renderers.base import RenderContext, to_primitive
from opennebula_cli.sdk.models.raw import RawCallResult


def render_raw(data: Any, *, ctx: RenderContext) -> None:
    """Render plain raw-ish output."""

    value = data.result if isinstance(data, RawCallResult) else data
    primitive = to_primitive(value)
    if isinstance(primitive, str):
        ctx.console.file.write(primitive)
        if not primitive.endswith("\n"):
            ctx.console.file.write("\n")
        return
    ctx.console.file.write(f"{json.dumps(primitive, sort_keys=True, separators=(',', ':'))}\n")
