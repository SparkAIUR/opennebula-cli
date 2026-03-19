"""Image commands."""

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.state import AppState

app = typer.Typer(no_args_is_help=True, help="Manage images.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


@app.command("list")
def list_images(ctx: typer.Context) -> None:
    """List images."""

    state = _state(ctx)
    try:
        state.render(state.client().image.list(), resource="image")
    except Exception as exc:
        raise_cli_error(exc)


@app.command("show")
def show_image(ctx: typer.Context, image_id: int) -> None:
    """Show an image."""

    state = _state(ctx)
    try:
        state.render(state.client().image.show(image_id), resource="image")
    except Exception as exc:
        raise_cli_error(exc)


@app.command("delete")
def delete_image(ctx: typer.Context, image_id: int) -> None:
    """Delete an image."""

    state = _state(ctx)
    try:
        state.render(state.client().image.delete(image_id), resource="image")
    except Exception as exc:
        raise_cli_error(exc)
