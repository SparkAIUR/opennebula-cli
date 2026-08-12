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
from opennebula_cli.cli.state import AppState
from opennebula_cli.config.endpoints import derive_service_endpoint
from opennebula_cli.sdk.exceptions import ConnectionError
from opennebula_cli.state_store import LOCK_ACTION_CHOICES, LockState, StateStore, StoredContext

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


def _context_payload(context: StoredContext, *, active_name: str | None) -> dict[str, object]:
    return {
        "name": context.name,
        "active": active_name == context.name,
        "endpoint": context.endpoint,
        "username": context.username,
        "version": context.version,
    }


def _emit_action(
    state: AppState,
    payload: dict[str, object],
    *,
    message: str,
    resource: str,
) -> None:
    """Keep friendly terminal messages while honoring machine-output contracts."""

    if state.output in {"table", "human"}:
        typer.echo(message)
        return
    state.render(payload, resource=resource)


def _lock_payload(lock_state: LockState) -> dict[str, object]:
    return {
        "enabled": lock_state.enabled,
        "actions": sorted(lock_state.actions),
        "commands": sorted(lock_state.commands),
        "password_set": lock_state.password_set,
    }


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


def _sync_auth_contexts_to_state_db() -> tuple[int, str]:
    """Copy auth config contexts into state DB and align active context."""

    config = load_auth_config()
    if config is None:
        raise typer.BadParameter(
            "Auth config was not found or is invalid. "
            "Set OPENNEBULA_CLI_AUTH_CONFIG and ensure current_context/contexts are valid."
        )

    current = config.resolve_current()
    if current is None:
        raise typer.BadParameter(
            "Auth config current_context does not match any configured context entry."
        )

    store = StateStore()
    for item in config.contexts:
        store.upsert_context(
            StoredContext(
                name=item.name,
                endpoint=item.endpoint,
                username=item.auth.username,
                password=item.auth.password,
                version=item.version,
            )
        )

    if not store.use_context(current.name):
        raise typer.BadParameter("Failed to set active context in state database after sync.")

    return len(config.contexts), current.name


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
    return str(password)


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

    state = require_state(ctx)
    try:
        selected_actions = _select_actions(actions)
        selected_commands = _select_commands(commands, selected_actions)
        selected_password = password
        if selected_password is None and state.output in {"table", "human"}:
            selected_password = _prompt_password()
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
        current = store.lock_state()
        _emit_action(
            state,
            _lock_payload(current),
            message=(
                "Commands locked successfully. To unlock, use `one state lock disable`"
                " and provide the password if one was set."
            ),
            resource="lock",
        )
    except Exception as exc:
        raise_cli_error(exc)


@lock_app.command("disable")
def lock_disable(
    ctx: typer.Context,
    yes: bool = typer.Option(False, "--yes", "-y", help="Disable without confirmation."),
) -> None:
    """Disable active command lock."""

    state = require_state(ctx)
    try:
        store = StateStore()
        current = store.lock_state()
        if not current.enabled:
            _emit_action(
                state,
                _lock_payload(current),
                message="No active lock found.",
                resource="lock",
            )
            return

        details = (
            f"actions={','.join(sorted(current.actions))}; "
            f"commands={','.join(sorted(current.commands))}"
        )
        should_disable = yes or typer.confirm(
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
        _emit_action(
            state,
            _lock_payload(store.lock_state()),
            message="Lock disabled successfully. The commands are now available for execution.",
            resource="lock",
        )
    except Exception as exc:
        raise_cli_error(exc)


@lock_app.command("status")
def lock_status(ctx: typer.Context) -> None:
    """Show the current command lock without exposing its password digest."""

    state = require_state(ctx)
    try:
        state.render(_lock_payload(StateStore().lock_state()), resource="lock")
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

    state = require_state(ctx)
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
        _emit_action(
            state,
            {"name": target_name, "active": True, "updated": True},
            message=(
                f"Context '{target_name}' set successfully. "
                f"You can switch to this context using `one state ctx use {target_name}`."
            ),
            resource="context-action",
        )
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("use")
def ctx_use(ctx: typer.Context, context_name: str) -> None:
    """Switch active context by name."""

    state = require_state(ctx)
    try:
        if _use_auth_config_contexts():
            ok = set_auth_current_context(context_name)
            if not ok:
                raise typer.BadParameter(f"Context '{context_name}' was not found in auth config.")
        else:
            store = StateStore()
            if not store.use_context(context_name):
                raise typer.BadParameter(
                    f"Context '{context_name}' was not found in state database."
                )
        _emit_action(
            state,
            {"name": context_name, "active": True},
            message=(
                f"Context switched to '{context_name}'. "
                "Subsequent commands will use this context for authentication and API interactions."
            ),
            resource="context-action",
        )
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("get")
def ctx_get(ctx: typer.Context) -> None:
    """Show the currently active context."""

    state = require_state(ctx)
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
            state.render(None, resource="context")
            return
        state.render(_context_payload(current, active_name=active_name), resource="context")
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

    state = require_state(ctx)
    try:
        selected_source = _ctx_source(source)
        contexts, active_name = _contexts_for_source(selected_source)
        if not contexts:
            state.render([], resource="context")
            return
        state.render(
            [_context_payload(context, active_name=active_name) for context in contexts],
            resource="context",
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

    state = require_state(ctx)
    try:
        selected_source = _ctx_source(source)
        contexts, active_name = _contexts_for_source(selected_source)
        if not contexts:
            state.render([], resource="context-validation")
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

        results: list[dict[str, object]] = []
        for item in selected_contexts:
            endpoint_overrides = (
                _auth_context_endpoints(item.name) if selected_source == "auth" else {}
            )
            try:
                from opennebula_cli.config.loader import resolve_runtime_config
                from opennebula_cli.sdk.client import OneClient

                config = resolve_runtime_config(
                    profile_name=None,
                    context_name=item.name,
                    require_context=item.name,
                    endpoint=None,
                    auth=None,
                    user=None,
                    password=None,
                    output="json",
                    no_pager=True,
                    timeout=timeout,
                    no_verify=False,
                    cert_dir=None,
                    verbose=0,
                    debug=False,
                )
                info = OneClient.from_config(config).server_info()
                results.append(
                    {
                        "context": item.name,
                        "service": "xmlrpc",
                        "ok": True,
                        "authenticated": True,
                        "server_version": info.version,
                        "profile": info.profile,
                        "endpoint": info.endpoint,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "context": item.name,
                        "service": "xmlrpc",
                        "ok": False,
                        "authenticated": False,
                        "detail": str(exc),
                    }
                )
            endpoints: list[tuple[str, str | None]] = [
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
                if endpoint_url is None:
                    results.append(
                        {
                            "context": item.name,
                            "service": label,
                            "ok": False,
                            "detail": "unresolved",
                        }
                    )
                    continue
                ok, detail = _check_endpoint(endpoint_url, timeout=timeout)
                results.append(
                    {
                        "context": item.name,
                        "service": label,
                        "ok": ok,
                        "authenticated": False,
                        "endpoint": endpoint_url,
                        "detail": detail,
                    }
                )

        state.render(results, resource="context-validation")
    except ConnectionError as exc:
        raise_cli_error(exc)
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("show")
def ctx_show(ctx: typer.Context, context_name: str) -> None:
    """Show details for a named context."""

    state = require_state(ctx)
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
        state.render(_context_payload(context, active_name=active_name), resource="context")
    except Exception as exc:
        raise_cli_error(exc)


@ctx_app.command("sync")
def ctx_sync(ctx: typer.Context) -> None:
    """Sync auth config contexts into the local state database."""

    state = require_state(ctx)
    try:
        count, active = _sync_auth_contexts_to_state_db()
        _emit_action(
            state,
            {"synced": count, "active_context": active},
            message=(
                f"Synced {count} context(s) from auth config to state database. "
                f"Active context: {active}."
            ),
            resource="context-action",
        )
    except Exception as exc:
        raise_cli_error(exc)
