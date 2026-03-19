"""VM commands."""

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.state import AppState

app = typer.Typer(no_args_is_help=True, help="Manage virtual machines.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


@app.command(
    "list",
    epilog=command_epilog("vm", "list", "--output json"),
)
def list_vms(ctx: typer.Context) -> None:
    """List VMs."""

    state = _state(ctx)
    try:
        state.render(state.client().vm.list(), resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "show",
    epilog=command_epilog("vm", "show", "42", "42 --output yaml"),
)
def show_vm(ctx: typer.Context, vm_id: int) -> None:
    """Show a VM."""

    state = _state(ctx)
    try:
        state.render(state.client().vm.show(vm_id), resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "poweroff",
    epilog=command_epilog(
        "vm",
        "poweroff",
        "42 --wait",
        "42 --hard --timeout 600",
        caution="This command changes live resources.",
    ),
)
def poweroff_vm(
    ctx: typer.Context,
    vm_id: int,
    hard: bool = typer.Option(False, "--hard", help="Use hard poweroff semantics."),
    wait: bool = typer.Option(False, "--wait", help="Wait for completion."),
    timeout: float = typer.Option(300.0, "--timeout", help="Wait timeout in seconds."),
    poll_interval: float = typer.Option(
        2.0,
        "--poll-interval",
        help="Polling interval in seconds.",
    ),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable progress display."),
) -> None:
    """Power off a VM."""

    state = _state(ctx)
    try:
        result = state.client().vm.poweroff(
            vm_id,
            hard=hard,
            wait=wait,
            timeout=timeout,
            poll_interval=poll_interval,
            show_progress=not no_progress,
        )
        state.render(result, resource="vm")
    except Exception as exc:
        raise_cli_error(exc)
