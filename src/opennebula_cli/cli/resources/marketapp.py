"""Marketapp commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(no_args_is_help=True, help="Manage market applications.")

register_official_commands(
    app,
    family="marketapp",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "create",
        "delete",
        "disable",
        "enable",
        "export",
        "list",
        "lock",
        "rename",
        "service-template",
        "show",
        "unlock",
        "update",
        "vm",
        "vm-template",
    ],
)
