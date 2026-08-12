"""JSON Lines renderer."""

from __future__ import annotations

import json
from typing import Any

from opennebula_cli.renderers.base import RenderContext, to_primitive


def render_jsonl(data: Any, *, ctx: RenderContext) -> None:
    payload = to_primitive(data)
    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        ctx.console.file.write(f"{json.dumps(item, sort_keys=True, separators=(',', ':'))}\n")
