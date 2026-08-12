"""onedb compatibility commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(
    no_args_is_help=True,
    help="Run onedb maintenance and migration compatibility commands.",
)

register_official_commands(
    app,
    family="db",
    commands=[
        "backup",
        "change-body",
        "change-history",
        "fsck",
        "history",
        "patch",
        "purge-done",
        "purge-history",
        "restore",
        "show-body",
        "show-history",
        "sqlite2mysql",
        "update-body",
        "update-history",
        "upgrade",
        "version",
    ],
)
