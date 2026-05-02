"""Group commands."""

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.state import AppState

app = typer.Typer(no_args_is_help=True, help="Manage groups.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


@app.command(
    "list",
    epilog=command_epilog("group", "list", "--output json"),
)
def list_groups(ctx: typer.Context) -> None:
    """List groups."""

    state = _state(ctx)
    try:
        state.render(state.client().group.list(), resource="group")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "show",
    epilog=command_epilog("group", "show", "0", "0 --output yaml"),
)
def show_group(ctx: typer.Context, group_id: int) -> None:
    """Show a group."""

    state = _state(ctx)
    try:
        state.render(state.client().group.show(group_id), resource="group")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="group",
    commands=[
        "addadmin",
        "batchquota",
        "create",
        "defaultquota",
        "deladmin",
        "delete",
        "quota",
        "update",
    ],
)
