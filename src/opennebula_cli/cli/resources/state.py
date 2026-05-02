"""State management commands."""

from __future__ import annotations

import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import typer

from opennebula_cli.auth.context_config import (
    FileContext,
    FileContextAuth,
    has_auth_config_file,
    load_auth_config,
    set_auth_current_context,
    upsert_auth_context,
)
from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.runtime import require_state
from opennebula_cli.config.endpoints import derive_service_endpoint
from opennebula_cli.sdk.exceptions import ConnectionError
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



def _print_context(context: StoredContext, *, active_name: str | None) -> None:
    active_label = " (active)" if active_name == context.name else ""
    typer.echo(f"name: {context.name}{active_label}")
    typer.echo(f"endpoint: {context.endpoint}")
    typer.echo(f"username: {context.username}")
    if context.version:
        typer.echo(f"version: {context.version}")


def _use_auth_config_contexts() -> bool:
    return has_auth_config_file() or bool(os.getenv("OPENNEBULA_CLI_AUTH_CONFIG"))


def _ctx_source(use_source: str) -> str:
    normalized = use_source.strip().lower()
    if normalized not in {"auto", "auth", "db"}:
        raise typer.BadParameter("--source must be one of: auto, auth, db")
    if normalized == "auto":
        return "auth" if _use_auth_config_contexts() else "db"
    return normalized


def _contexts_for_source(source: str) -> tuple[list[StoredContext], str | None]:
    if source == "auth":
        config = load_auth_config()
        contexts = [
            StoredContext(
                name=item.name,
                endpoint=item.endpoint,
                username=item.auth.username,
                password=item.auth.password,
                version=item.version,
            )
            for item in (config.contexts if config else ())
        ]
        return contexts, (config.current_context if config else None)

    store = StateStore()
    return store.list_contexts(), store.active_context_name()


def _auth_context_endpoints(name: str) -> dict[str, str]:
    config = load_auth_config()
    selected = config.resolve_named(name) if config else None
    return dict(selected.endpoints or {}) if selected else {}


def _check_endpoint(url: str, *, timeout: float) -> tuple[bool, str]:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = getattr(response, "status", 200)
            return (status_code < 500, f"HTTP {status_code}")
    except HTTPError as exc:
        status_ok = exc.code < 500
        return (status_ok, f"HTTP {exc.code}")
    except URLError as exc:
        reason = str(exc.reason) if exc.reason is not None else "connection error"
        return (False, reason)


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


def _allow_empty_command_scope(actions: set[str]) -> bool:
    """Whether an action scope can intentionally lock all commands."""

    return actions == {"delete"}


def _select_commands(commands_raw: str | None, actions: set[str]) -> set[str]:
    if commands_raw is not None:
        selected = _parse_csv_values(commands_raw)
    else:
        typer.echo("Which commands do you want to lock?")
        typer.echo("Available: all, others, " + ", ".join(KNOWN_COMMANDS))
        raw = typer.prompt("Commands (comma-separated, use others to add custom)", default="")
        selected = _parse_csv_values(raw)

    if not selected:
        if _allow_empty_command_scope(actions):
            return set()
        raise typer.BadParameter("At least one command must be selected.")

    if "others" in selected:
        extra_raw = typer.prompt("Enter additional commands (comma-separated)", default="")
        selected.remove("others")
        selected |= _parse_csv_values(extra_raw)

    if "all" in selected:
        return {"all"}

    selected = {item for item in selected if item}
    if not selected:
        if _allow_empty_command_scope(actions):
            return set()
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

    require_state(ctx)  # keep state callback contract
    try:
        selected_actions = _select_actions(actions)
        selected_commands = _select_commands(commands, selected_actions)
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

    require_state(ctx)  # keep state callback contract
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

    require_state(ctx)  # keep state callback contract
    try:
        target_name = name or typer.prompt("Enter a name for this context")
        target_endpoint = endpoint or typer.prompt("Enter the OpenNebula endpoint URL")
        target_user = user or typer.prompt("Enter your OpenNebula username")
        target_password = password
        if target_password is None:
            target_password = typer.prompt("Enter your OpenNebula password", hide_input=True)

        if _use_auth_config_contexts():
            upsert_auth_context(
                FileContext(
                    name=target_name,
                    endpoint=target_endpoint,
                    auth=FileContextAuth(username=target_user, password=target_password),
                    version=version,
                ),
                set_current=True,
            )
        else:
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

    require_state(ctx)  # keep state callback contract
    try:
        if _use_auth_config_contexts():
            ok = set_auth_current_context(context_name)
            if not ok:
                raise typer.BadParameter(
                    f"Context '{context_name}' was not found in auth config."
                )
        else:
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

    require_state(ctx)
    try:
        if _use_auth_config_contexts():
            config = load_auth_config()
            current_file = config.resolve_current() if config else None
            current = (
                StoredContext(
                    name=current_file.name,
                    endpoint=current_file.endpoint,
                    username=current_file.auth.username,
                    password=current_file.auth.password,
                    version=current_file.version,
                )
                if current_file
                else None
            )
            active_name = config.current_context if config else None
        else:
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
def ctx_list(
    ctx: typer.Context,
    source: str = typer.Option(
        "auto",
        "--source",
        help="Context backend source: auto|auth|db",
    ),
) -> None:
    """List all stored contexts."""

    require_state(ctx)
    try:
        selected_source = _ctx_source(source)
        contexts, active_name = _contexts_for_source(selected_source)
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


@ctx_app.command("validate")
def ctx_validate(
    ctx: typer.Context,
    source: str = typer.Option(
        "auto",
        "--source",
        help="Context backend source: auto|auth|db",
    ),
    all_contexts: bool = typer.Option(False, "--all", help="Validate all contexts."),
    context: str | None = typer.Option(None, "--context", help="Validate a specific context name."),
    timeout: float = typer.Option(5.0, "--timeout", help="Per-endpoint timeout in seconds."),
) -> None:
    """Validate endpoint reachability for one or more contexts."""

    require_state(ctx)
    try:
        selected_source = _ctx_source(source)
        contexts, active_name = _contexts_for_source(selected_source)
        if not contexts:
            typer.echo("No contexts found.")
            return

        selected_contexts = contexts
        if context:
            selected_contexts = [item for item in contexts if item.name == context]
            if not selected_contexts:
                raise typer.BadParameter(
                    f"Context '{context}' was not found in {selected_source} source."
                )
        elif not all_contexts:
            selected_contexts = [item for item in contexts if item.name == active_name]
            if not selected_contexts:
                raise typer.BadParameter(
                    "No active context is set. "
                    "Use `one state ctx use <name>` or pass --all/--context."
                )

        total = 0
        passed = 0
        for item in selected_contexts:
            typer.echo(f"Context: {item.name}")
            endpoint_overrides = (
                _auth_context_endpoints(item.name) if selected_source == "auth" else {}
            )
            endpoints: list[tuple[str, str | None]] = [
                ("xmlrpc", item.endpoint),
                (
                    "oneflow",
                    derive_service_endpoint(
                        item.endpoint,
                        service="oneflow",
                        explicit=endpoint_overrides.get("oneflow"),
                    ),
                ),
                (
                    "firestone",
                    derive_service_endpoint(
                        item.endpoint,
                        service="firestone",
                        explicit=endpoint_overrides.get("firestone"),
                    ),
                ),
                (
                    "web",
                    derive_service_endpoint(
                        item.endpoint,
                        service="web",
                        explicit=endpoint_overrides.get("web"),
                    ),
                ),
            ]

            for label, endpoint_url in endpoints:
                total += 1
                typer.echo(f"  checking {label}: {endpoint_url}")
                if endpoint_url is None:
                    typer.echo("    FAIL  unable to resolve endpoint")
                    continue
                ok, detail = _check_endpoint(endpoint_url, timeout=timeout)
                if ok:
                    passed += 1
                    typer.echo(f"    PASS  {detail}")
                else:
                    typer.echo(f"    FAIL  {detail}")

        typer.echo(f"Validation complete: {passed}/{total} checks passed")
    except ConnectionError as exc:
        raise_cli_error(exc)
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("show")
def ctx_show(ctx: typer.Context, context_name: str) -> None:
    """Show details for a named context."""

    require_state(ctx)
    try:
        if _use_auth_config_contexts():
            config = load_auth_config()
            selected = config.resolve_named(context_name) if config else None
            context = (
                StoredContext(
                    name=selected.name,
                    endpoint=selected.endpoint,
                    username=selected.auth.username,
                    password=selected.auth.password,
                    version=selected.version,
                )
                if selected
                else None
            )
            active_name = config.current_context if config else None
            not_found_source = "auth config"
        else:
            store = StateStore()
            context = store.get_context(context_name)
            active_name = store.active_context_name()
            not_found_source = "state database"
        if context is None:
            raise typer.BadParameter(
                f"Context '{context_name}' was not found in {not_found_source}."
            )
        _print_context(context, active_name=active_name)
    except Exception as exc:
        raise_cli_error(exc)
