"""Image commands."""


import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.runtime import require_state

app = typer.Typer(no_args_is_help=True, help="Manage images.")



@app.command(
    "list",
    epilog=command_epilog("image", "list", "--output json"),
)
def list_images(ctx: typer.Context) -> None:
    """List images."""

    state = require_state(ctx)
    try:
        state.render(state.client().image.list(), resource="image")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "show",
    epilog=command_epilog("image", "show", "18", "18 --output yaml"),
)
def show_image(
    ctx: typer.Context,
    image_id: int,
    full: bool = typer.Option(False, "--full", help="Return lossless normalized backend data."),
) -> None:
    """Show an image."""

    state = require_state(ctx)
    try:
        result = (
            state.client().image.show_full(image_id)
            if full
            else state.client().image.show(image_id)
        )
        state.render(result, resource="image")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "owner",
    epilog=command_epilog("image", "owner", "18 --output json"),
)
def image_owner(ctx: typer.Context, image_id: int) -> None:
    """Summarize image VM ownership for recovery triage."""

    state = require_state(ctx)
    try:
        state.render(state.client().image.owner(image_id), resource="image-owner")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "delete",
    epilog=command_epilog(
        "image",
        "delete",
        "18",
        "18 --output json",
        caution="This command changes live resources.",
    ),
)
def delete_image(ctx: typer.Context, image_id: int) -> None:
    """Delete an image."""

    state = require_state(ctx)
    try:
        state.render(state.client().image.delete(image_id), resource="image")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="image",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "chtype",
        "clone",
        "create",
        "disable",
        "enable",
        "lock",
        "nonpersistent",
        "orphans",
        "persistent",
        "rename",
        "restore",
        "snapshot-delete",
        "snapshot-flatten",
        "snapshot-revert",
        "top",
        "unlock",
        "update",
    ],
)
