"""Vrouter commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage virtual routers.")

register_official_commands(
    app,
    family="vrouter",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "create",
        "delete",
        "instantiate",
        "list",
        "lock",
        "nic-attach",
        "nic-detach",
        "rename",
        "show",
        "top",
        "unlock",
        "update",
    ],
)
