"""CLI exception handling helpers."""

from __future__ import annotations

import typer

from opennebula_cli.sdk.exceptions import (
    ApiError,
    AuthError,
    ConnectionError,
    PluginError,
    TimeoutError,
)


def raise_cli_error(exc: Exception) -> None:
    """Convert SDK errors into Typer exits."""

    code = 1
    if isinstance(exc, AuthError):
        code = 10
    elif isinstance(exc, ConnectionError):
        code = 11
    elif isinstance(exc, ApiError):
        code = 12
    elif isinstance(exc, TimeoutError):
        code = 14
    elif isinstance(exc, PluginError):
        code = 20
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code)
