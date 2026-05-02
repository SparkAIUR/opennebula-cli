"""log commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage log commands.")

register_official_commands(
    app,
    family="log",
    commands=[
        "get",
        "get-service",
        "get-vm",
    ],
)
