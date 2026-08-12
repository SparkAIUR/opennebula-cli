"""acct commands."""

import typer

app = typer.Typer(
    no_args_is_help=True,
    help="Inspect and run account and showback compatibility operations.",
)
