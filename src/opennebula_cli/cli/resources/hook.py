"""hook commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage hook commands.")

register_official_commands(
    app,
    family="hook",
    commands=[
        "create",
        "delete",
        "list",
        "lock",
        "log",
        "rename",
        "retry",
        "show",
        "top",
        "unlock",
        "update",
    ],
)
