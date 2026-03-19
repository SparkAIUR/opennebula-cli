"""YAML renderer."""

from __future__ import annotations

from typing import Any

import yaml

from opennebula_cli.renderers.base import RenderContext, to_primitive


def render_yaml(data: Any, *, ctx: RenderContext) -> None:
    """Render YAML output."""

    ctx.console.print(yaml.safe_dump(to_primitive(data), sort_keys=True))
