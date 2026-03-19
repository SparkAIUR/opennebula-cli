"""Cluster commands."""

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.state import AppState

app = typer.Typer(no_args_is_help=True, help="Manage clusters.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


@app.command(
    "list",
    epilog=command_epilog("cluster", "list", "--output json"),
)
def list_clusters(ctx: typer.Context) -> None:
    """List clusters."""

    state = _state(ctx)
    try:
        state.render(state.client().cluster.list(), resource="cluster")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "show",
    epilog=command_epilog("cluster", "show", "0", "0 --output yaml"),
)
def show_cluster(ctx: typer.Context, cluster_id: int) -> None:
    """Show a cluster."""

    state = _state(ctx)
    try:
        state.render(state.client().cluster.show(cluster_id), resource="cluster")
    except Exception as exc:
        raise_cli_error(exc)
