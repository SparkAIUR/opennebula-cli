"""VM commands."""

from typing import Literal, cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.help_examples import command_epilog
from opennebula_cli.cli.resources.official import register_official_commands
from opennebula_cli.cli.state import AppState

app = typer.Typer(no_args_is_help=True, help="Manage virtual machines.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


def _parse_duration(value: str) -> float:
    normalized = value.strip().lower()
    if not normalized:
        raise typer.BadParameter("Duration cannot be empty.")
    multiplier = 1.0
    if normalized[-1] in {"s", "m", "h"}:
        suffix = normalized[-1]
        normalized = normalized[:-1]
        multiplier = {"s": 1.0, "m": 60.0, "h": 3600.0}[suffix]
    try:
        seconds = float(normalized) * multiplier
    except ValueError as exc:
        raise typer.BadParameter("Duration must be seconds or use s, m, or h suffix.") from exc
    if seconds <= 0:
        raise typer.BadParameter("Duration must be greater than zero.")
    return seconds


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
def show_vm(
    ctx: typer.Context,
    vm_id: int,
    full: bool = typer.Option(False, "--full", help="Return lossless normalized backend data."),
    output: str | None = typer.Option(
        None,
        "--output",
        help="Override output format for this command: table|json|yaml|xml|csv|raw",
    ),
) -> None:
    """Show a VM."""

    state = _state(ctx)
    try:
        result = state.client().vm.show_full(vm_id) if full else state.client().vm.show(vm_id)
        state.render(result, resource="vm", output_override=output)
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "disk-list",
    epilog=command_epilog("vm", "disk-list", "42 --output json"),
)
def disk_list_vm(ctx: typer.Context, vm_id: int) -> None:
    """List disks attached to a VM."""

    state = _state(ctx)
    try:
        state.render(state.client().vm.disk_list(vm_id), resource="vm-disk")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "disk-attach",
    epilog=command_epilog(
        "vm",
        "disk-attach",
        "42 --image-id 18",
        "42 --image-id 18 --dev-prefix vd --target vdb --output json",
        caution="This command changes live resources.",
    ),
)
def disk_attach_vm(
    ctx: typer.Context,
    vm_id: int,
    image_id: int = typer.Option(..., "--image-id", help="Image ID to attach."),
    dev_prefix: str | None = typer.Option(
        None,
        "--dev-prefix",
        "--prefix",
        help="Override the image DEV_PREFIX.",
    ),
    target: str | None = typer.Option(None, "--target", help="Target device name."),
    driver: str | None = typer.Option(None, "--driver", help="Disk driver."),
    cache: str | None = typer.Option(None, "--cache", help="Hypervisor cache mode."),
    readonly: bool = typer.Option(False, "--readonly", help="Attach disk as read-only."),
) -> None:
    """Attach an image as a VM disk."""

    state = _state(ctx)
    try:
        result = state.client().vm.disk_attach(
            vm_id,
            image_id=image_id,
            dev_prefix=dev_prefix,
            target=target,
            driver=driver,
            cache=cache,
            readonly=readonly,
        )
        state.render(result, resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "disk-detach",
    epilog=command_epilog(
        "vm",
        "disk-detach",
        "42 --disk-id 1",
        caution="This command changes live resources.",
    ),
)
def disk_detach_vm(
    ctx: typer.Context,
    vm_id: int,
    disk_id: int = typer.Option(..., "--disk-id", help="Disk ID to detach."),
) -> None:
    """Detach a disk from a VM."""

    state = _state(ctx)
    try:
        state.render(state.client().vm.disk_detach(vm_id, disk_id=disk_id), resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "recover",
    epilog=command_epilog(
        "vm",
        "recover",
        "42 --retry",
        "42 --success --output json",
        caution="This command changes live resources.",
    ),
)
def recover_vm(
    ctx: typer.Context,
    vm_id: int,
    success: bool = typer.Option(False, "--success", help="Succeed the pending action."),
    failure: bool = typer.Option(False, "--failure", help="Fail the pending action."),
    retry: bool = typer.Option(False, "--retry", help="Retry the last failed action."),
    delete: bool = typer.Option(
        False,
        "--delete",
        help="Delete the VM when no recovery is possible.",
    ),
) -> None:
    """Recover a VM stuck in a driver operation."""

    selected = [
        name
        for name, enabled in (
            ("success", success),
            ("failure", failure),
            ("retry", retry),
            ("delete", delete),
        )
        if enabled
    ]
    if len(selected) != 1:
        raise typer.BadParameter(
            "Select exactly one of --success, --failure, --retry, or --delete."
        )
    state = _state(ctx)
    try:
        operation = cast(Literal["success", "failure", "retry", "delete"], selected[0])
        result = state.client().vm.recover(vm_id, operation)
        state.render(result, resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "reboot",
    epilog=command_epilog(
        "vm",
        "reboot",
        "42",
        caution="This command changes live resources.",
    ),
)
def reboot_vm(ctx: typer.Context, vm_id: int) -> None:
    """Reboot a VM."""

    state = _state(ctx)
    try:
        state.render(state.client().vm.action(vm_id, "reboot"), resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "reboot-hard",
    epilog=command_epilog(
        "vm",
        "reboot-hard",
        "42",
        caution="This command changes live resources.",
    ),
)
def reboot_hard_vm(ctx: typer.Context, vm_id: int) -> None:
    """Hard reboot a VM."""

    state = _state(ctx)
    try:
        state.render(state.client().vm.action(vm_id, "reboot-hard"), resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "resume",
    epilog=command_epilog(
        "vm",
        "resume",
        "42",
        caution="This command changes live resources.",
    ),
)
def resume_vm(ctx: typer.Context, vm_id: int) -> None:
    """Resume a VM."""

    state = _state(ctx)
    try:
        state.render(state.client().vm.action(vm_id, "resume"), resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


@app.command(
    "wait",
    epilog=command_epilog("vm", "wait", "42 --state ACTIVE --lcm-state RUNNING --timeout 10m"),
)
def wait_vm(
    ctx: typer.Context,
    vm_id: int,
    expected_state: str = typer.Option(..., "--state", help="Expected VM state label."),
    lcm_state: str | None = typer.Option(None, "--lcm-state", help="Expected LCM state label."),
    timeout: str = typer.Option("300", "--timeout", help="Timeout in seconds, or s/m/h suffix."),
    poll_interval: float = typer.Option(
        2.0,
        "--poll-interval",
        help="Polling interval in seconds.",
    ),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable progress display."),
) -> None:
    """Wait for a VM state."""

    parsed_timeout = _parse_duration(timeout)
    state = _state(ctx)
    try:
        result = state.client().vm.wait_state(
            vm_id,
            state=expected_state,
            lcm_state=lcm_state,
            timeout=parsed_timeout,
            poll_interval=poll_interval,
            show_progress=not no_progress,
        )
        state.render(result, resource="vm")
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


@app.command(
    "poweroff-hard",
    epilog=command_epilog(
        "vm",
        "poweroff-hard",
        "42 --wait",
        caution="This command changes live resources.",
    ),
)
def poweroff_hard_vm(
    ctx: typer.Context,
    vm_id: int,
    wait: bool = typer.Option(False, "--wait", help="Wait for completion."),
    timeout: float = typer.Option(300.0, "--timeout", help="Wait timeout in seconds."),
    poll_interval: float = typer.Option(
        2.0,
        "--poll-interval",
        help="Polling interval in seconds.",
    ),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable progress display."),
) -> None:
    """Hard power off a VM."""

    state = _state(ctx)
    try:
        result = state.client().vm.poweroff(
            vm_id,
            hard=True,
            wait=wait,
            timeout=timeout,
            poll_interval=poll_interval,
            show_progress=not no_progress,
        )
        state.render(result, resource="vm")
    except Exception as exc:
        raise_cli_error(exc)


register_official_commands(
    app,
    family="vm",
    commands=[
        "backup",
        "backup-cancel",
        "backupmode",
        "chgrp",
        "chmod",
        "chown",
        "create",
        "create-chart",
        "delete-chart",
        "deploy",
        "disk-resize",
        "disk-saveas",
        "disk-snapshot-create",
        "disk-snapshot-delete",
        "disk-snapshot-list",
        "disk-snapshot-rename",
        "disk-snapshot-revert",
        "hold",
        "lock",
        "migrate",
        "nic-attach",
        "nic-detach",
        "nic-update",
        "pci-attach",
        "pci-detach",
        "port-forward",
        "release",
        "rename",
        "resched",
        "resize",
        "restore",
        "save",
        "sched-delete",
        "sched-update",
        "sg-attach",
        "sg-detach",
        "snapshot-create",
        "snapshot-delete",
        "snapshot-list",
        "snapshot-revert",
        "ssh",
        "stop",
        "suspend",
        "terminate",
        "top",
        "undeploy",
        "unlock",
        "unresched",
        "update",
        "update-chart",
        "updateconf",
        "vnc",
    ],
)
