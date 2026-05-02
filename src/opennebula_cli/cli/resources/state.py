"""State management commands."""

from __future__ import annotations

from typing import cast

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.state import AppState
from opennebula_cli.state_store import LOCK_ACTION_CHOICES, StateStore, StoredContext

app = typer.Typer(no_args_is_help=True, help="Manage local CLI state, locks, and contexts.")
lock_app = typer.Typer(no_args_is_help=True, help="Manage command execution locks.")
ctx_app = typer.Typer(no_args_is_help=True, help="Manage local OpenNebula contexts.")
app.add_typer(lock_app, name="lock")
app.add_typer(ctx_app, name="ctx")

KNOWN_COMMANDS = (
    "vm",
    "host",
    "image",
    "template",
    "vnet",
    "datastore",
    "cluster",
    "user",
    "group",
    "acl",
    "flow",
    "flow-template",
    "gate",
    "marketapp",
    "db",
    "vdc",
    "vrouter",
    "vmgroup",
    "vntemplate",
    "zone",
    "hook",
    "market",
    "secgroup",
    "cfg",
    "log",
    "swap",
    "showback",
    "acct",
    "gather",
    "workflow",
    "raw",
)


def _state(ctx: typer.Context) -> AppState:
    return cast(AppState, ctx.obj)


def _print_context(context: StoredContext, *, active_name: str | None) -> None:
    active_label = " (active)" if active_name == context.name else ""
    typer.echo(f"name: {context.name}{active_label}")
    typer.echo(f"endpoint: {context.endpoint}")
    typer.echo(f"username: {context.username}")
    if context.version:
        typer.echo(f"version: {context.version}")


def _parse_csv_values(raw: str | None) -> set[str]:
    if raw is None:
        return set()
    return {token.strip().lower() for token in raw.split(",") if token.strip()}


def _select_actions(actions_raw: str | None) -> set[str]:
    if actions_raw:
        selected = _parse_csv_values(actions_raw)
    else:
        typer.echo("Which actions do you want to lock?")
        typer.echo("Available: create, delete, update, list, show, all")
        raw = typer.prompt("Actions (comma-separated)", default="delete")
        selected = _parse_csv_values(raw)

    if not selected:
        raise typer.BadParameter("At least one action must be selected.")
    invalid = sorted(item for item in selected if item not in LOCK_ACTION_CHOICES)
    if invalid:
        raise typer.BadParameter(f"Unsupported action(s): {', '.join(invalid)}")
    if "all" in selected:
        return {"all"}
    return selected


def _select_commands(commands_raw: str | None) -> set[str]:
    if commands_raw:
        selected = _parse_csv_values(commands_raw)
    else:
        typer.echo("Which commands do you want to lock?")
        typer.echo("Available: all, others, " + ", ".join(KNOWN_COMMANDS))
        raw = typer.prompt("Commands (comma-separated, use others to add custom)", default="")
        selected = _parse_csv_values(raw)

    if not selected:
        raise typer.BadParameter("At least one command must be selected.")

    if "others" in selected:
        extra_raw = typer.prompt("Enter additional commands (comma-separated)", default="")
        selected.remove("others")
        selected |= _parse_csv_values(extra_raw)

    if "all" in selected:
        return {"all"}

    selected = {item for item in selected if item}
    if not selected:
        raise typer.BadParameter("At least one concrete command must be selected.")
    return selected


def _prompt_password() -> str | None:
    password = typer.prompt(
        "Enter a password to lock the commands (optional, press enter to skip)",
        default="",
        hide_input=True,
        show_default=False,
    )
    if not password:
        return None
    confirmation = typer.prompt("Confirm password", hide_input=True, show_default=False)
    if confirmation != password:
        raise typer.BadParameter("Password confirmation does not match.")
    return password


@lock_app.command("enable")
def lock_enable(
    ctx: typer.Context,
    actions: str | None = typer.Option(
        None,
        "--actions",
        help="Comma-separated actions: create,delete,update,list,show,all",
    ),
    commands: str | None = typer.Option(
        None,
        "--commands",
        help="Comma-separated commands or 'all'.",
    ),
    password: str | None = typer.Option(None, "--password", hide_input=True),
) -> None:
    """Enable command lock with action and command filters."""

    _state(ctx)  # keep state callback contract
    try:
        selected_actions = _select_actions(actions)
        selected_commands = _select_commands(commands)
        selected_password = password if password is not None else _prompt_password()
        if selected_password is not None and password is not None:
            confirmation = typer.prompt("Confirm password", hide_input=True, show_default=False)
            if confirmation != selected_password:
                raise typer.BadParameter("Password confirmation does not match.")

        store = StateStore()
        store.set_lock(
            actions=selected_actions,
            commands=selected_commands,
            password=selected_password,
        )
        typer.echo(
            "Commands locked successfully. To unlock, use `one state lock disable`"
            " and provide the password if one was set."
        )
    except Exception as exc:
        raise_cli_error(exc)


@lock_app.command("disable")
def lock_disable(ctx: typer.Context) -> None:
    """Disable active command lock."""

    _state(ctx)  # keep state callback contract
    try:
        store = StateStore()
        current = store.lock_state()
        if not current.enabled:
            typer.echo("No active lock found.")
            return

        details = (
            f"actions={','.join(sorted(current.actions))}; "
            f"commands={','.join(sorted(current.commands))}"
        )
        should_disable = typer.confirm(
            f"A lock is currently active ({details}). Do you want to disable it?",
            default=True,
        )
        if not should_disable:
            typer.echo("Lock remains active.")
            return

        if current.password_set:
            supplied = typer.prompt("Enter the password to disable the lock", hide_input=True)
            if not store.verify_lock_password(supplied):
                raise typer.BadParameter("Incorrect password. Lock remains active.")

        store.disable_lock()
        typer.echo("Lock disabled successfully. The commands are now available for execution.")
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("set")
def ctx_set(
    ctx: typer.Context,
    name: str | None = typer.Option(None, "--name", help="Context name."),
    endpoint: str | None = typer.Option(None, "--endpoint", help="OpenNebula endpoint URL."),
    user: str | None = typer.Option(None, "--user", help="OpenNebula username."),
    password: str | None = typer.Option(
        None,
        "--password",
        hide_input=True,
        help="OpenNebula password.",
    ),
    version: str | None = typer.Option(
        None,
        "--version",
        help="Optional OpenNebula version label.",
    ),
) -> None:
    """Create or update a local context and mark it active."""

    _state(ctx)  # keep state callback contract
    try:
        target_name = name or typer.prompt("Enter a name for this context")
        target_endpoint = endpoint or typer.prompt("Enter the OpenNebula endpoint URL")
        target_user = user or typer.prompt("Enter your OpenNebula username")
        target_password = password
        if target_password is None:
            target_password = typer.prompt("Enter your OpenNebula password", hide_input=True)

        store = StateStore()
        store.upsert_context(
            StoredContext(
                name=target_name,
                endpoint=target_endpoint,
                username=target_user,
                password=target_password,
                version=version,
            )
        )
        typer.echo(
            f"Context '{target_name}' set successfully. "
            f"You can switch to this context using `one state ctx use {target_name}`."
        )
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("use")
def ctx_use(ctx: typer.Context, context_name: str) -> None:
    """Switch active context by name."""

    _state(ctx)  # keep state callback contract
    try:
        store = StateStore()
        if not store.use_context(context_name):
            raise typer.BadParameter(
                f"Context '{context_name}' was not found in state database."
            )
        typer.echo(
            f"Context switched to '{context_name}'. "
            "Subsequent commands will use this context for authentication and API interactions."
        )
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("get")
def ctx_get(ctx: typer.Context) -> None:
    """Show the currently active context."""

    _state(ctx)
    try:
        store = StateStore()
        current = store.get_active_context()
        active_name = store.active_context_name()
        if current is None:
            typer.echo("No active context is set.")
            return
        _print_context(current, active_name=active_name)
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("list")
def ctx_list(ctx: typer.Context) -> None:
    """List all stored contexts."""

    _state(ctx)
    try:
        store = StateStore()
        contexts = store.list_contexts()
        active_name = store.active_context_name()
        if not contexts:
            typer.echo("No contexts found.")
            return
        for context in contexts:
            suffix = " (active)" if context.name == active_name else ""
            version = f", version={context.version}" if context.version else ""
            typer.echo(
                f"- {context.name}{suffix}: endpoint={context.endpoint}, "
                f"user={context.username}{version}"
            )
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("show")
def ctx_show(ctx: typer.Context, context_name: str) -> None:
    """Show details for a named context."""

    _state(ctx)
    try:
        store = StateStore()
        context = store.get_context(context_name)
        active_name = store.active_context_name()
        if context is None:
            raise typer.BadParameter(
                f"Context '{context_name}' was not found in state database."
            )
        _print_context(context, active_name=active_name)
    except Exception as exc:
        raise_cli_error(exc)
