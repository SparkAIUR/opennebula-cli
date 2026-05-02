"""Virtual network commands."""

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.state import AppState

app = typer.Typer(no_args_is_help=True, help="Manage virtual networks.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


@app.command(
    "list",
    epilog=command_epilog("vnet", "list", "--output json"),
)
def list_vnets(ctx: typer.Context) -> None:
    """List virtual networks."""

    state = _state(ctx)
    try:
        state.render(state.client().vnet.list(), resource="vnet")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "show",
    epilog=command_epilog("vnet", "show", "11", "11 --output yaml"),
)
def show_vnet(ctx: typer.Context, vnet_id: int) -> None:
    """Show a virtual network."""

    state = _state(ctx)
    try:
        state.render(state.client().vnet.show(vnet_id), resource="vnet")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="vnet",
    commands=[
        "addar",
        "addleases",
        "chgrp",
        "chmod",
        "chown",
        "create",
        "delete",
        "free",
        "hold",
        "lock",
        "orphans",
        "recover",
        "release",
        "rename",
        "reserve",
        "rmar",
        "rmleases",
        "unlock",
        "update",
        "updatear",
    ],
)
