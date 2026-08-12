"""secgroup commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage security group compatibility operations.")

register_official_commands(
    app,
    family="secgroup",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "clone",
        "commit",
        "create",
        "delete",
        "list",
        "rename",
        "show",
        "update",
    ],
)
