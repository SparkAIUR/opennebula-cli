"""ACL commands."""


import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.runtime import require_state

app = typer.Typer(no_args_is_help=True, help="Manage ACL rules.")



@app.command(
    "list",
    epilog=command_epilog("acl", "list", "--output json"),
)
def list_acl(ctx: typer.Context) -> None:
    """List ACL rules."""

    state = require_state(ctx)
    try:
        state.render(state.client().acl.list(), resource="acl")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="acl",
    commands=[
        "create",
        "delete",
    ],
)
