"""XML renderer."""

from __future__ import annotations

from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from opennebula_cli.renderers.base import RenderContext, to_primitive


def _append(parent: Element, key: str, value: Any) -> None:
    node = SubElement(parent, key)
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            _append(node, child_key, child_value)
    elif isinstance(value, list):
        for item in value:
            _append(node, "item", item)
    else:
        node.text = "" if value is None else str(value)


def render_xml(data: Any, *, ctx: RenderContext) -> None:
    """Render XML output."""

    root = Element(ctx.resource or "result")
    primitive = to_primitive(data)
    if isinstance(primitive, dict):
        for key, value in primitive.items():
            _append(root, str(key), value)
    elif isinstance(primitive, list):
        for item in primitive:
            _append(root, "item", item)
    else:
        root.text = str(primitive)
    ctx.console.print(tostring(root, encoding="unicode"))
