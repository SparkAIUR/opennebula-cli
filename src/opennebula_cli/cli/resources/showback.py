"""showback commands."""

import typer

from opennebula_cli.cli.resources.official import register_official_commands

app = typer.Typer(
    no_args_is_help=True,
    help="Inspect showback and accounting compatibility operations.",
)

register_official_commands(
    app,
    family="showback",
    commands=[
        "calculate",
        "list",
    ],
)
