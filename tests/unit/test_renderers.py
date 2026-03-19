from __future__ import annotations

from io import StringIO

from rich.console import Console

from opennebula_cli.renderers import render_output
from opennebula_cli.renderers.base import RenderContext


def render_text(data: object, output: str) -> str:
    stream = StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None)
    render_output(
        data,
        ctx=RenderContext(
            console=console,
            output=output,
            interactive=False,
            no_pager=True,
            resource=None,
        ),
    )
    return stream.getvalue()


def test_json_renderer_is_deterministic() -> None:
    text = render_text({"b": 1, "a": 2}, "json")
    assert '"a": 2' in text
    assert '"b": 1' in text


def test_csv_renderer_outputs_header() -> None:
    text = render_text([{"id": 1, "name": "alpha"}], "csv")
    assert "id,name" in text
