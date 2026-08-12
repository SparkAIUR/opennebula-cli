"""User commands."""

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.runtime import require_state

app = typer.Typer(no_args_is_help=True, help="Manage users.")


@app.command(
    "list",
    epilog=command_epilog("user", "list", "--output json"),
)
def list_users(ctx: typer.Context) -> None:
    """List users."""

    state = require_state(ctx)
    try:
        state.render(state.client().user.list(), resource="user")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "show",
    epilog=command_epilog("user", "show", "0", "0 --output yaml"),
)
def show_user(ctx: typer.Context, user_id: int) -> None:
    """Show a user."""

    state = require_state(ctx)
    try:
        state.render(state.client().user.show(user_id), resource="user")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="user",
    commands=[
        "addgroup",
        "batchquota",
        "chauth",
        "chgrp",
        "create",
        "defaultquota",
        "delete",
        "delgroup",
        "disable",
        "enable",
        "encode",
        "key",
        "login",
        "passwd",
        "passwdsearch",
        "quota",
        "token-create",
        "token-delete",
        "token-delete-all",
        "token-set",
        "umask",
        "update",
    ],
)
