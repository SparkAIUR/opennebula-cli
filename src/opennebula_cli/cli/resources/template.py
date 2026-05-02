"""Template commands."""


import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.runtime import require_state

app = typer.Typer(no_args_is_help=True, help="Manage VM templates.")



@app.command(
    "list",
    epilog=command_epilog("template", "list", "--output json"),
)
def list_templates(ctx: typer.Context) -> None:
    """List templates."""

    state = require_state(ctx)
    try:
        state.render(state.client().template.list(), resource="template")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "show",
    epilog=command_epilog("template", "show", "24", "24 --output yaml"),
)
def show_template(ctx: typer.Context, template_id: int) -> None:
    """Show a template."""

    state = require_state(ctx)
    try:
        state.render(state.client().template.show(template_id), resource="template")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "delete",
    epilog=command_epilog(
        "template",
        "delete",
        "24",
        "24 --output json",
        caution="This command changes live resources.",
    ),
)
def delete_template(ctx: typer.Context, template_id: int) -> None:
    """Delete a template."""

    state = require_state(ctx)
    try:
        state.render(state.client().template.delete(template_id), resource="template")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "instantiate",
    epilog=command_epilog(
        "template",
        "instantiate",
        "24",
        '24 --name "build-vm"',
        caution="This command changes live resources.",
    ),
)
def instantiate_template(
    ctx: typer.Context,
    template_id: int,
    name: str | None = typer.Option(None, "--name", help="Override the VM name."),
) -> None:
    """Instantiate a template."""

    state = require_state(ctx)
    try:
        result = state.client().template.instantiate(template_id, name=name)
        state.render(result, resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="template",
    commands=[
        "chgrp",
        "chmod",
        "chown",
        "clone",
        "create",
        "lock",
        "rename",
        "top",
        "unlock",
        "update",
    ],
)
