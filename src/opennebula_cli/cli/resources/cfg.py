"""cfg commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage cfg commands.")

register_official_commands(
    app,
    family="cfg",
    commands=[
        "diff",
        "generate",
        "init",
        "patch",
        "status",
        "upgrade",
        "validate",
    ],
)
