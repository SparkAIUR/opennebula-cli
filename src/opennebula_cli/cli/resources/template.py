"""Template commands."""

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.state import AppState

app = typer.Typer(no_args_is_help=True, help="Manage VM templates.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


@app.command("list")
def list_templates(ctx: typer.Context) -> None:
    """List templates."""

    state = _state(ctx)
    try:
        state.render(state.client().template.list(), resource="template")
    except Exception as exc:
        raise_cli_error(exc)


@app.command("show")
def show_template(ctx: typer.Context, template_id: int) -> None:
    """Show a template."""

    state = _state(ctx)
    try:
        state.render(state.client().template.show(template_id), resource="template")
    except Exception as exc:
        raise_cli_error(exc)


@app.command("delete")
def delete_template(ctx: typer.Context, template_id: int) -> None:
    """Delete a template."""

    state = _state(ctx)
    try:
        state.render(state.client().template.delete(template_id), resource="template")
    except Exception as exc:
        raise_cli_error(exc)


@app.command("instantiate")
def instantiate_template(
    ctx: typer.Context,
    template_id: int,
    name: str | None = typer.Option(None, "--name", help="Override the VM name."),
) -> None:
    """Instantiate a template."""

    state = _state(ctx)
    try:
        result = state.client().template.instantiate(template_id, name=name)
        state.render(result, resource="template")
    except Exception as exc:
        raise_cli_error(exc)
