"""XML renderer."""

from __future__ import annotations

from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from opennebula_cli.renderers.base import RenderContext, to_primitive


def _append(parent: Element, key: str, value: Any, *, official_schema: bool) -> None:
    if isinstance(value, list) and official_schema:
        for item in value:
            _append(parent, key, item, official_schema=True)
        return
    node = SubElement(parent, key)
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            _append(node, child_key, child_value, official_schema=official_schema)
    elif isinstance(value, list):
        for item in value:
            _append(node, "item", item, official_schema=False)
    else:
        node.text = "" if value is None else str(value)


def render_xml(data: Any, *, ctx: RenderContext) -> None:
    """Render XML output."""

    root = Element(ctx.resource or "result")
    primitive = to_primitive(data)
    if isinstance(primitive, dict):
        for key, value in primitive.items():
            _append(root, str(key), value, official_schema=ctx.official_schema)
    elif isinstance(primitive, list):
        for item in primitive:
            _append(root, "item", item, official_schema=ctx.official_schema)
    else:
        root.text = str(primitive)
    ctx.console.file.write(f"{tostring(root, encoding='unicode')}\n")
