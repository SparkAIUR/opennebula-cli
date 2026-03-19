"""Host commands."""

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.state import AppState

app = typer.Typer(no_args_is_help=True, help="Manage hosts.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


@app.command("list")
def list_hosts(ctx: typer.Context) -> None:
    """List hosts."""

    state = _state(ctx)
    try:
        state.render(state.client().host.list(), resource="host")
    except Exception as exc:
        raise_cli_error(exc)


@app.command("show")
def show_host(ctx: typer.Context, host_id: int) -> None:
    """Show a host."""

    state = _state(ctx)
    try:
        state.render(state.client().host.show(host_id), resource="host")
    except Exception as exc:
        raise_cli_error(exc)


@app.command("flush")
def flush_host(ctx: typer.Context, host_id: int) -> None:
    """Flush a host."""

    state = _state(ctx)
    try:
        state.render(state.client().host.flush(host_id), resource="host")
    except Exception as exc:
        raise_cli_error(exc)
