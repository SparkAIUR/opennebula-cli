"""Helpers for registering captured official commands."""

from __future__ import annotations

from typing import Any, cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.state import AppState

COMMAND_CONTEXT = {"allow_extra_args": True, "ignore_unknown_options": True}


def _describe_official_command(family: str, command_name: str) -> str:
    """Build a descriptive help line for an official parity command."""

    normalized = command_name.replace("-", " ")
    return (
        f"Execute `{family} {command_name}` with official-style arguments and options. "
        f"This compatibility path forwards `{normalized}` through the parity service layer."
    )


def register_official_commands(app: typer.Typer, *, family: str, commands: list[str]) -> None:
    """Register loose-argument official parity commands for a resource family."""

    for command_name in commands:
        app.command(
            command_name,
            help=_describe_official_command(family, command_name),
            context_settings=COMMAND_CONTEXT,
            epilog=command_epilog(
                family,
                command_name,
                "[official args/options] --output json",
                caution="This command may change live resources depending on the official verb.",
            ),
        )(_make_official_command(family, command_name))


def _make_official_command(family: str, command_name: str) -> Any:
    def official_command(ctx: typer.Context) -> None:
        """Execute a captured official command through the parity service layer."""

        state = cast(AppState, ctx.obj)
        try:
            service = cast(Any, getattr(state.client(), family))
            result = service.run_official(command_name, list(ctx.args))
            state.render(result, resource=family)
        except Exception as exc:
            raise_cli_error(exc)

    official_command.__name__ = f"{family}_{command_name.replace('-', '_')}"
    official_command.__doc__ = _describe_official_command(family, command_name)
    return official_command
