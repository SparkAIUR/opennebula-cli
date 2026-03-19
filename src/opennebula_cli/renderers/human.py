"""Human-readable renderers."""

from __future__ import annotations

from typing import Any

from rich.json import JSON
from rich.table import Table

from opennebula_cli.renderers.base import RenderContext, to_primitive
from opennebula_cli.renderers.views import DEFAULT_VIEWS, ColumnSpec


def render_human(data: Any, *, ctx: RenderContext) -> None:
    """Render resource data in human-oriented form."""

    normalized = to_primitive(data)
    if isinstance(normalized, list):
        render_table(normalized, ctx=ctx)
        return
    ctx.console.print(JSON.from_data(normalized))


def render_table(items: list[dict[str, object]], *, ctx: RenderContext) -> None:
    """Render a list of normalized mappings."""

    view = DEFAULT_VIEWS.get(ctx.resource or "")
    if not items:
        ctx.console.print("No results.")
        return
    if not ctx.interactive:
        columns = [column.key for column in (view.columns if view else [])] or list(items[0].keys())
        for item in items:
            ctx.console.print("\t".join(str(item.get(column, "")) for column in columns))
        return
    table = Table(show_header=True, header_style="bold cyan")
    column_specs: list[ColumnSpec] = list(view.columns) if view else []
    if not column_specs:
        for key in items[0].keys():
            table.add_column(str(key).upper())
    else:
        for column in column_specs:
            table.add_column(column.label, justify=column.justify)
    for item in items:
        if column_specs:
            table.add_row(*(str(item.get(column.key, "")) for column in column_specs))
        else:
            table.add_row(*(str(value) for value in item.values()))
    ctx.console.print(table)
