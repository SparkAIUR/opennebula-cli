"""Renderer dispatch."""

from __future__ import annotations

from typing import Any

from opennebula_cli.renderers.base import RenderContext
from opennebula_cli.renderers.csv import render_csv
from opennebula_cli.renderers.human import render_human
from opennebula_cli.renderers.json import render_json
from opennebula_cli.renderers.raw import render_raw
from opennebula_cli.renderers.xml import render_xml
from opennebula_cli.renderers.yaml import render_yaml


def render_output(data: Any, *, ctx: RenderContext) -> None:
    """Dispatch to the selected output renderer."""

    output = "table" if ctx.output == "human" else ctx.output
    if output == "table":
        render_human(data, ctx=ctx)
    elif output == "json":
        render_json(data, ctx=ctx)
    elif output == "yaml":
        render_yaml(data, ctx=ctx)
    elif output == "xml":
        render_xml(data, ctx=ctx)
    elif output == "csv":
        render_csv(data, ctx=ctx)
    else:
        render_raw(data, ctx=ctx)
