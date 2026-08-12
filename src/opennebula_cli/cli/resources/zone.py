"""zone commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage OpenNebula zone compatibility operations.")

register_official_commands(
    app,
    family="zone",
    commands=[
        "create",
        "delete",
        "disable",
        "enable",
        "list",
        "rename",
        "server-add",
        "server-del",
        "server-reset",
        "serversync",
        "set",
        "show",
        "update",
    ],
)
