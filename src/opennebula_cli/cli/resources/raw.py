"""Guarded raw XML-RPC commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.runtime import require_state
from opennebula_cli.sdk.client import OneClient

app = typer.Typer(no_args_is_help=True, help="Run guarded raw XML-RPC calls.")



def _load_args(json_args: Path | None, json_args_text: str | None) -> list[Any]:
    sources = [source is not None for source in (json_args, json_args_text)]
    if sum(sources) != 1:
        raise typer.BadParameter("Provide exactly one of --json-args or --json-args-text.")
    try:
        if json_args is not None:
            payload = json.loads(json_args.read_text(encoding="utf-8"))
        else:
            payload = json.loads(str(json_args_text))
    except OSError as exc:
        raise typer.BadParameter(f"Unable to read JSON args file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON args: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise typer.BadParameter("JSON args must be an array of positional XML-RPC arguments.")
    return payload


@app.command(
    "call",
    epilog=(
        "Examples:\n"
        "  one --output json raw call one.vm.info --json-args-text '[42]' "
        "--i-understand-this-is-unsafe\n"
        "  one --output json raw call one.vm.info --json-args ./args.json "
        "--i-understand-this-is-unsafe"
    ),
)
def raw_call(
    ctx: typer.Context,
    method: str,
    json_args: Annotated[
        Path | None,
        typer.Option("--json-args", help="Path to a JSON array of positional XML-RPC arguments."),
    ] = None,
    json_args_text: Annotated[
        str | None,
        typer.Option("--json-args-text", help="Inline JSON array of positional XML-RPC arguments."),
    ] = None,
    unsafe: Annotated[
        bool,
        typer.Option(
            "--i-understand-this-is-unsafe",
            help="Required acknowledgement for raw XML-RPC calls.",
        ),
    ] = False,
) -> None:
    """Call an arbitrary XML-RPC method."""

    if not unsafe:
        raise typer.BadParameter("Raw calls require --i-understand-this-is-unsafe.")
    args = _load_args(json_args, json_args_text)
    state = require_state(ctx)
    try:
        raw_client = OneClient.from_config(state.resolve_config(), backend="raw")
        state.render(raw_client.raw.call(method, args), resource="raw")
    except Exception as exc:
        raise_cli_error(exc)
