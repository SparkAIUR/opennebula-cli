"""CLI exception handling helpers."""

from __future__ import annotations

import json

import click
import typer

from opennebula_cli.cli.state import AppState
from opennebula_cli.sdk.exceptions import (
    ApiError,
    ApiFault,
    AuthError,
    ConnectionError,
    PartialFailureError,
    PluginError,
    PolicyError,
    TimeoutError,
    TlsError,
    UnsupportedCapabilityError,
)


def raise_cli_error(exc: Exception) -> None:
    """Convert SDK errors into Typer exits."""

    code = 1
    if isinstance(exc, AuthError):
        code = 10
    elif isinstance(exc, TimeoutError):
        code = 14
    elif isinstance(exc, TlsError):
        code = 13
    elif isinstance(exc, ConnectionError):
        code = 11
    elif isinstance(exc, (ApiError, ApiFault)):
        code = 12
    elif isinstance(exc, UnsupportedCapabilityError):
        code = 15
    elif isinstance(exc, PolicyError):
        code = 16
    elif isinstance(exc, PartialFailureError):
        code = 17
    elif isinstance(exc, PluginError):
        code = 20

    ctx = click.get_current_context(silent=True)
    state = ctx.find_object(AppState) if ctx is not None else None
    output = getattr(state, "output", "table")
    machine = output in {"json", "jsonl", "yaml", "xml", "csv", "raw", "plain"}
    if machine:
        if hasattr(exc, "error_detail"):
            detail = exc.error_detail()
        else:
            detail = {
                "schema_version": "1",
                "type": "internal_error",
                "message": str(exc),
            }
        typer.echo(json.dumps({"error": detail}, separators=(",", ":")), err=True)
    else:
        typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code)
