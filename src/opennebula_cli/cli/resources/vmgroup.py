"""Vmgroup commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(
    no_args_is_help=True,
    help="Manage VM group policies and actions through compatibility commands.",
)

register_official_commands(
    app,
    family="vmgroup",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "create",
        "delete",
        "list",
        "lock",
        "rename",
        "role-add",
        "role-delete",
        "role-update",
        "show",
        "unlock",
        "update",
    ],
)
