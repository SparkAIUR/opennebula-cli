"""OneFlow service template commands."""

from __future__ import annotations

from typing import Any, cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.state import AppState
from opennebula_cli.services.flow_template import OneFlowTemplateService

COMMAND_CONTEXT = {"allow_extra_args": True, "ignore_unknown_options": True}

app = typer.Typer(no_args_is_help=True, help="Manage OneFlow service templates.")


def _describe_flow_template_command(command_name: str) -> str:
    return (
        "Execute `flow-template "
        f"{command_name}` using official-style arguments and the OneFlow template adapter."
    )



def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)



def _make_official_command(command_name: str) -> Any:
    def official_command(ctx: typer.Context) -> None:
        """Execute a OneFlow-template command through the parity REST adapter."""

        state = _state(ctx)
        try:
            service = OneFlowTemplateService(state.resolve_config())
            result = service.run_official(command_name, list(ctx.args))
            state.render(result, resource="flow-template")
        except Exception as exc:
            raise_cli_error(exc)

    official_command.__name__ = f"flow_template_{command_name.replace('-', '_')}"
    official_command.__doc__ = _describe_flow_template_command(command_name)
    return official_command


for _command_name in [
    "chgrp",
    "chmod",
    "chown",
    "clone",
    "create",
    "delete",
    "instantiate",
    "list",
    "rename",
    "show",
    "top",
    "update",
]:
    app.command(
        _command_name,
        help=_describe_flow_template_command(_command_name),
        context_settings=COMMAND_CONTEXT,
        epilog=command_epilog(
            "flow-template",
            _command_name,
            "[official args/options] --output json",
            caution="This command may change live resources depending on the official verb.",
        ),
    )(_make_official_command(_command_name))
