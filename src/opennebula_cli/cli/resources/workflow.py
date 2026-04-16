"""Workflow commands."""

# ruff: noqa: B008

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.state import AppState
from opennebula_cli.services.workflow_template import WorkflowTemplateService
from opennebula_cli.services.workflow_vm import WorkflowVmInitService

app = typer.Typer(no_args_is_help=True, help="Manage workflow automation commands.")
template_app = typer.Typer(no_args_is_help=True, help="Render and import workflow VM templates.")
vm_app = typer.Typer(no_args_is_help=True, help="Initialize VMs from workflow definitions.")
app.add_typer(template_app, name="template")
app.add_typer(vm_app, name="vm")
TARGET_DIR_ARGUMENT = typer.Argument(Path("."), help="Directory to write starter workflow files.")


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


def _workflow_epilog(group: str, *examples: str, caution: str | None = None) -> str:
    lines: list[str] = []
    if caution:
        lines.append(caution)
        lines.append("")
    lines.append("Examples:")
    for suffix in examples:
        lines.append(f"  one workflow {group} {suffix}")
    return "\n".join(lines)


@template_app.command(
    "init",
    epilog=_workflow_epilog(
        "template",
        "init",
        "init ./openclaw-workflow",
        "init ./openclaw-workflow --force",
    ),
)
def init_template_workflow(
    target_dir: Path = TARGET_DIR_ARGUMENT,
    force: bool = typer.Option(False, "--force", help="Overwrite existing starter files."),
) -> None:
    """Initialize starter workflow files."""

    service = WorkflowTemplateService()
    try:
        created = service.init(target_dir, force=force)
        resolved_target = target_dir.expanduser().resolve()
        typer.echo(f"Initialized workflow template scaffold in {resolved_target}:")
        for path in created:
            typer.echo(f"  {path}")
    except Exception as exc:
        raise_cli_error(exc)


@template_app.command(
    "render",
    epilog=_workflow_epilog(
        "template",
        "render workflow.yaml",
        "render workflow.yaml --vars-file vars.example.yaml",
        "render workflow.yaml --var template_name=openclaw-user-a --output-file rendered.one",
    ),
)
def render_template_workflow(
    workflow_file: Path,
    vars_file: Path | None = typer.Option(None, "--vars-file", help="Path to YAML/JSON vars file."),
    var: list[str] | None = typer.Option(
        None,
        "--var",
        help="Set render variables as key=value pairs. Repeatable.",
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output-file",
        help="Write rendered template to a file instead of stdout.",
    ),
) -> None:
    """Render a workflow file to OpenNebula template text."""

    service = WorkflowTemplateService()
    try:
        rendered = service.render_workflow(
            workflow_file,
            vars_file=vars_file,
            cli_vars=var or [],
            require_template_name=False,
        )
        if output_file is not None:
            destination = output_file.expanduser().resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered.template_text, encoding="utf-8")
            typer.echo(str(destination))
            return
        typer.echo(rendered.template_text, nl=False)
    except Exception as exc:
        raise_cli_error(exc)


@template_app.command(
    "import",
    epilog=_workflow_epilog(
        "template",
        "import workflow.yaml --vars-file vars.example.yaml",
        "import workflow.yaml --var template_name=openclaw-template",
        caution="This command changes live resources.",
    ),
)
def import_template_workflow(
    ctx: typer.Context,
    workflow_file: Path,
    vars_file: Path | None = typer.Option(None, "--vars-file", help="Path to YAML/JSON vars file."),
    var: list[str] | None = typer.Option(
        None,
        "--var",
        help="Set render variables as key=value pairs. Repeatable.",
    ),
) -> None:
    """Render and import a workflow-backed template."""

    state = _state(ctx)
    service = WorkflowTemplateService(template_service=state.client().template)
    try:
        result = service.import_workflow(workflow_file, vars_file=vars_file, cli_vars=var or [])
        state.render(result, resource="template")
    except Exception as exc:
        raise_cli_error(exc)


@template_app.command(
    "apply",
    epilog=_workflow_epilog(
        "template",
        "apply workflow.yaml --vars-file vars.example.yaml",
        "apply workflow.yaml --var template_name=openclaw-template --output-file rendered.one",
        caution="This command changes live resources.",
    ),
)
def apply_template_workflow(
    ctx: typer.Context,
    workflow_file: Path,
    vars_file: Path | None = typer.Option(None, "--vars-file", help="Path to YAML/JSON vars file."),
    var: list[str] | None = typer.Option(
        None,
        "--var",
        help="Set render variables as key=value pairs. Repeatable.",
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output-file",
        help="Write rendered OpenNebula template text to this file before import.",
    ),
) -> None:
    """Render, optionally write, and import a workflow-backed template."""

    state = _state(ctx)
    service = WorkflowTemplateService(template_service=state.client().template)
    try:
        result = service.import_workflow(
            workflow_file,
            vars_file=vars_file,
            cli_vars=var or [],
            rendered_output_file=output_file,
        )
        state.render(result, resource="template")
    except Exception as exc:
        raise_cli_error(exc)


@vm_app.command(
    "init",
    epilog=_workflow_epilog(
        "vm",
        "init --name alice --template-name openclaw-template "
        "--set global.resources.ram=8Gi --set global.context.OPENCLAW_USER=alice",
        "init bulk-init.yaml --vm-name alice --wait-ready",
        "init bulk-init.yaml --index 0 --template-id 24",
        caution="This command changes live resources.",
    ),
)
def init_vm_workflow(
    ctx: typer.Context,
    workflow_file: Path | None = typer.Argument(
        None,
        help="Workflow VM YAML file. Optional for inline single VM mode.",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="VM base name for inline single VM mode (no file).",
    ),
    vm_name: str | None = typer.Option(
        None,
        "--vm-name",
        help="Select VM entry by `name` when file has multiple entries.",
    ),
    index: int | None = typer.Option(
        None,
        "--index",
        help="Select VM entry by zero-based index when file has multiple entries.",
    ),
    template_id: int | None = typer.Option(
        None,
        "--template-id",
        help="Override template by ID.",
    ),
    template_name: str | None = typer.Option(
        None,
        "--template-name",
        help="Override template by name.",
    ),
    set_value: list[str] | None = typer.Option(
        None,
        "--set",
        help="Apply dot-path overrides as path=value. Repeatable.",
    ),
    wait_ready: bool = typer.Option(
        False,
        "--wait-ready",
        help="Wait for VM state ACTIVE/RUNNING.",
    ),
    timeout: float = typer.Option(300.0, "--timeout", help="Wait timeout in seconds."),
    poll_interval: float = typer.Option(
        2.0,
        "--poll-interval",
        help="Polling interval in seconds.",
    ),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable wait progress display."),
) -> None:
    """Initialize a single VM from workflow configuration."""

    state = _state(ctx)
    service = WorkflowVmInitService(
        template_service=state.client().template,
        vm_service=state.client().vm,
    )
    try:
        summary = service.init_single(
            workflow_file=workflow_file,
            name=name,
            selector_name=vm_name,
            selector_index=index,
            set_values=set_value or [],
            template_id=template_id,
            template_name=template_name,
            wait_ready=wait_ready,
            timeout=timeout,
            poll_interval=poll_interval,
            show_progress=not no_progress,
        )
        state.render(summary)
        if int(summary.get("failed", 0)) > 0:
            raise typer.Exit(code=12)
    except typer.Exit:
        raise
    except Exception as exc:
        raise_cli_error(exc)


@vm_app.command(
    "apply",
    epilog=_workflow_epilog(
        "vm",
        "apply bulk-init.yaml",
        "apply bulk-init.yaml --wait-ready --set global.name_prefix=user-vm-",
        "apply bulk-init.yaml --template-name openclaw-template",
        caution="This command changes live resources.",
    ),
)
def apply_vm_workflow(
    ctx: typer.Context,
    workflow_file: Path,
    template_id: int | None = typer.Option(
        None,
        "--template-id",
        help="Override template by ID for all VMs.",
    ),
    template_name: str | None = typer.Option(
        None,
        "--template-name",
        help="Override template by name for all VMs.",
    ),
    set_value: list[str] | None = typer.Option(
        None,
        "--set",
        help="Apply dot-path overrides as path=value. Repeatable.",
    ),
    wait_ready: bool = typer.Option(
        False,
        "--wait-ready",
        help="Wait for each VM state ACTIVE/RUNNING.",
    ),
    timeout: float = typer.Option(300.0, "--timeout", help="Wait timeout in seconds."),
    poll_interval: float = typer.Option(
        2.0,
        "--poll-interval",
        help="Polling interval in seconds.",
    ),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable wait progress display."),
) -> None:
    """Initialize multiple VMs from a workflow file."""

    state = _state(ctx)
    service = WorkflowVmInitService(
        template_service=state.client().template,
        vm_service=state.client().vm,
    )
    try:
        summary = service.apply_bulk(
            workflow_file,
            set_values=set_value or [],
            template_id=template_id,
            template_name=template_name,
            wait_ready=wait_ready,
            timeout=timeout,
            poll_interval=poll_interval,
            show_progress=not no_progress,
        )
        state.render(summary)
        if int(summary.get("failed", 0)) > 0:
            raise typer.Exit(code=12)
    except typer.Exit:
        raise
    except Exception as exc:
        raise_cli_error(exc)
