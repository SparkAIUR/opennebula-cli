"""market commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage market commands.")

register_official_commands(
    app,
    family="market",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "create",
        "delete",
        "disable",
        "enable",
        "list",
        "rename",
        "show",
        "update",
    ],
)
