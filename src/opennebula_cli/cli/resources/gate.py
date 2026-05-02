"""OneGate compatibility commands."""

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.state import AppState

app = typer.Typer(
    no_args_is_help=True,
    help="Access OneGate VM context and metadata compatibility commands.",
)


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


@app.command("vm-show", epilog=command_epilog("gate", "vm-show", "42 --output json"))
def vm_show(ctx: typer.Context) -> None:
    """Show VM info through onegate compatibility path."""

    state = _state(ctx)
    try:
        state.render(state.client().gate.run_official("vm-show", list(ctx.args)), resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="gate",
    commands=[
        "vm-update",
        "resume",
        "stop",
        "suspend",
        "terminate",
        "reboot",
        "poweroff",
        "resched",
        "unresched",
        "hold",
        "release",
        "service-show",
        "service-scale",
        "vrouter-show",
        "vnet-show",
    ],
)
