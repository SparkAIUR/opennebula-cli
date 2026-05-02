"""VNTEMPLATE commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage virtual network templates.")

register_official_commands(
    app,
    family="vntemplate",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "clone",
        "create",
        "delete",
        "instantiate",
        "list",
        "lock",
        "rename",
        "show",
        "top",
        "unlock",
        "update",
    ],
)
