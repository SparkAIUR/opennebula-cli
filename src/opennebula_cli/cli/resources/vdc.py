"""VDC commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage VDC resources.")

register_official_commands(
    app,
    family="vdc",
    commands=[
        "addcluster",
        "adddatastore",
        "addgroup",
        "addhost",
        "addvnet",
        "create",
        "delcluster",
        "deldatastore",
        "delete",
        "delgroup",
        "delhost",
        "delvnet",
        "list",
        "rename",
        "show",
        "update",
    ],
)
