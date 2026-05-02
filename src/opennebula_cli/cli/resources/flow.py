"""OneFlow service commands."""

from __future__ import annotations

from typing import Any

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.official_help_texts import official_command_description
from opennebula_cli.cli.runtime import require_state

COMMAND_CONTEXT = {"allow_extra_args": True, "ignore_unknown_options": True}

app = typer.Typer(no_args_is_help=True, help="Manage OneFlow services.")


def _describe_flow_command(command_name: str) -> str:
    official = official_command_description("flow", command_name)
    if official:
        return official
    return (
        f"Execute `flow {command_name}` using official-style arguments and the OneFlow "
        "REST parity adapter."
    )



def _make_official_command(command_name: str) -> Any:
    def official_command(ctx: typer.Context) -> None:
        """Execute a OneFlow compatibility command through the REST parity adapter."""

        state = require_state(ctx)
        try:
            result = state.client().flow.run_official(command_name, list(ctx.args))
            state.render(result, resource="flow")
        except Exception as exc:
            raise_cli_error(exc)

    official_command.__name__ = f"flow_{command_name.replace('-', '_')}"
    official_command.__doc__ = _describe_flow_command(command_name)
    return official_command


for _command_name in [
    "action",
    "add-role",
    "chgrp",
    "chmod",
    "chown",
    "delete",
    "list",
    "purge-done",
    "recover",
    "release",
    "remove-role",
    "rename",
    "scale",
    "service",
    "show",
    "top",
    "update",
]:
    app.command(
        _command_name,
        help=_describe_flow_command(_command_name),
        context_settings=COMMAND_CONTEXT,
        epilog=command_epilog(
            "flow",
            _command_name,
            "[official args/options] --output json",
            caution="This command may change live resources depending on the official verb.",
        ),
    )(_make_official_command(_command_name))
