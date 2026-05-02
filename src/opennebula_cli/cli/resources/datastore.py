"""Datastore commands."""


import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.runtime import require_state

app = typer.Typer(no_args_is_help=True, help="Manage datastores.")



@app.command(
    "list",
    epilog=command_epilog("datastore", "list", "--output json"),
)
def list_datastores(ctx: typer.Context) -> None:
    """List datastores."""

    state = require_state(ctx)
    try:
        state.render(state.client().datastore.list(), resource="datastore")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "show",
    epilog=command_epilog("datastore", "show", "5", "5 --output yaml"),
)
def show_datastore(ctx: typer.Context, datastore_id: int) -> None:
    """Show a datastore."""

    state = require_state(ctx)
    try:
        state.render(state.client().datastore.show(datastore_id), resource="datastore")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="datastore",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "create",
        "delete",
        "disable",
        "enable",
        "rename",
        "update",
    ],
)
