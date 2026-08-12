"""CSV renderer."""

from __future__ import annotations

import csv
import io
from typing import Any

from opennebula_cli.renderers.base import RenderContext, to_primitive


def render_csv(data: Any, *, ctx: RenderContext) -> None:
    """Render list data as CSV."""

    rows = to_primitive(data)
    if not isinstance(rows, list) or not rows:
        ctx.console.file.write("\n")
        return
    fieldnames = list(rows[0].keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    if not ctx.no_header:
        writer.writeheader()
    for row in rows:
        writer.writerow(row)
    ctx.console.file.write(f"{buffer.getvalue().rstrip()}\n")
