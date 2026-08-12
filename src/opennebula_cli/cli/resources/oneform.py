"""OpenNebula 7.4 OneForm command families."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import typer

from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.runtime import require_state
from opennebula_cli.services.official import parse_id_list

COMMAND_CONTEXT = {"allow_extra_args": True, "ignore_unknown_options": True}

form_app = typer.Typer(no_args_is_help=True, help="Manage OneForm drivers.")
provider_app = typer.Typer(no_args_is_help=True, help="Manage OneForm providers.")
provision_app = typer.Typer(no_args_is_help=True, help="Manage OneForm provisions.")
provider_template_app = typer.Typer(
    no_args_is_help=True, help="Guarded-preview OneForm provider templates."
)
provision_template_app = typer.Typer(
    no_args_is_help=True, help="Guarded-preview OneForm provision templates."
)


def _json_file(path: str | None) -> dict[str, object]:
    if path is None:
        return {}
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(f"Unable to read JSON input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise typer.BadParameter("JSON input must be an object")
    return {str(key): item for key, item in value.items()}


def _parsed(ctx: typer.Context) -> tuple[list[str], dict[str, str], set[str]]:
    from opennebula_cli.services.official import parse_official_args

    parsed = parse_official_args(list(ctx.args))
    return parsed.positionals, parsed.options, parsed.flags


@form_app.command("list", context_settings=COMMAND_CONTEXT)
@form_app.command("top", context_settings=COMMAND_CONTEXT)
def form_list(ctx: typer.Context) -> None:
    state = require_state(ctx)
    try:
        _, _, flags = _parsed(ctx)
        state.render(state.client().form.list(enabled="enabled" in flags), resource="form")
    except Exception as exc:
        raise_cli_error(exc)


@form_app.command("show")
def form_show(ctx: typer.Context, driver_name: str) -> None:
    state = require_state(ctx)
    try:
        state.render(state.client().form.show(driver_name), resource="form")
    except Exception as exc:
        raise_cli_error(exc)


@form_app.command("sync")
def form_sync(ctx: typer.Context) -> None:
    state = require_state(ctx)
    try:
        state.render(state.client().form.sync(), resource="form")
    except Exception as exc:
        raise_cli_error(exc)


def _form_enable(ctx: typer.Context, driver_name: str, *, enabled: bool) -> None:
    state = require_state(ctx)
    try:
        state.render(state.client().form.enable(driver_name, enabled=enabled), resource="form")
    except Exception as exc:
        raise_cli_error(exc)


@form_app.command("enable")
def form_enable(ctx: typer.Context, driver_name: str) -> None:
    _form_enable(ctx, driver_name, enabled=True)


@form_app.command("disable")
def form_disable(ctx: typer.Context, driver_name: str) -> None:
    _form_enable(ctx, driver_name, enabled=False)


def _provider_command(command: str) -> Any:
    def invoke(ctx: typer.Context) -> None:
        state = require_state(ctx)
        try:
            positionals, options, flags = _parsed(ctx)
            service = state.client().provider
            result: object
            if command in {"list", "top"}:
                result = service.list(enabled="enabled" in flags, sensitive="sensitive" in flags)
            elif command == "show":
                result = service.show(int(positionals[0]), sensitive="sensitive" in flags)
            elif command == "create":
                result = service.create(
                    positionals[0], _json_file(positionals[1] if len(positionals) > 1 else None)
                )
            elif command == "update":
                result = service.update(
                    int(positionals[0]),
                    _json_file(positionals[1] if len(positionals) > 1 else None),
                )
            elif command == "rename":
                result = service.update(int(positionals[0]), {"name": positionals[1]})
            else:
                ids = parse_id_list(positionals[0])
                if command == "delete":
                    body: Mapping[str, object] = {}
                elif command == "chmod":
                    body = {"octet": positionals[1]}
                elif command == "chgrp":
                    body = {"group_id": int(positionals[1])}
                else:
                    body = {
                        "owner_id": int(positionals[1]),
                        "group_id": int(positionals[2]) if len(positionals) > 2 else None,
                    }
                result = [service.action(identifier, command, body) for identifier in ids]
            state.render(result, resource="provider")
        except (IndexError, ValueError) as exc:
            raise_cli_error(typer.BadParameter(f"Invalid arguments for provider {command}: {exc}"))
        except Exception as exc:
            raise_cli_error(exc)

    invoke.__name__ = f"provider_{command.replace('-', '_')}"
    return invoke


for _provider_verb in [
    "list",
    "top",
    "show",
    "create",
    "update",
    "rename",
    "chgrp",
    "chown",
    "chmod",
    "delete",
]:
    provider_app.command(_provider_verb, context_settings=COMMAND_CONTEXT)(
        _provider_command(_provider_verb)
    )


def _provision_command(command: str) -> Any:
    def invoke(ctx: typer.Context) -> None:
        state = require_state(ctx)
        try:
            positionals, options, flags = _parsed(ctx)
            service = state.client().provision
            result: object
            if command in {"list", "top"}:
                result = service.list()
            elif command == "show":
                result = service.show(int(positionals[0]), sensitive="sensitive" in flags)
            elif command == "create":
                create_body = _json_file(positionals[3] if len(positionals) > 3 else None)
                result = service.create(
                    {
                        "driver": positionals[0],
                        "deployment_type": positionals[1],
                        "provider_id": int(positionals[2]),
                        **create_body,
                    }
                )
            elif command in {"update", "rename"}:
                update_body = (
                    {"name": positionals[1]}
                    if command == "rename"
                    else _json_file(positionals[1] if len(positionals) > 1 else None)
                )
                result = service.update(int(positionals[0]), update_body)
            elif command == "logs":
                result = service.logs(int(positionals[0]), all_logs="all" in flags)
            else:
                identifier = int(positionals[0])
                action = {
                    "deprovision": "undeploy",
                    "del-host": "scale",
                    "add-host": "scale",
                    "add-ip": "add-ip",
                    "del-ip": "remove-ip",
                }.get(command, command)
                action_body: dict[str, object] = {"force": "force" in flags}
                if command in {"add-host", "del-host"}:
                    action_body.update(
                        direction="up" if command == "add-host" else "down",
                        nodes=options.get("host_ids", "").split(",")
                        if options.get("host_ids")
                        else [],
                        amount=int(options.get("amount", "1")),
                    )
                elif command == "add-ip":
                    action_body = {"amount": int(options.get("amount", "1"))}
                elif command == "del-ip":
                    action_body = {"ar_id": int(positionals[1])}
                elif command == "chmod":
                    action_body = {"octet": positionals[1]}
                elif command == "chgrp":
                    action_body = {"group_id": int(positionals[1])}
                elif command == "chown":
                    action_body = {
                        "owner_id": int(positionals[1]),
                        "group_id": int(positionals[2]) if len(positionals) > 2 else None,
                    }
                result = service.action(identifier, action, action_body)
            state.render(result, resource="provision")
        except (IndexError, ValueError) as exc:
            raise_cli_error(typer.BadParameter(f"Invalid arguments for provision {command}: {exc}"))
        except Exception as exc:
            raise_cli_error(exc)

    invoke.__name__ = f"provision_{command.replace('-', '_')}"
    return invoke


for _provision_verb in [
    "list",
    "top",
    "show",
    "create",
    "update",
    "rename",
    "chgrp",
    "chown",
    "chmod",
    "retry",
    "add-host",
    "del-host",
    "add-ip",
    "del-ip",
    "deprovision",
    "delete",
    "logs",
]:
    provision_app.command(_provision_verb, context_settings=COMMAND_CONTEXT)(
        _provision_command(_provision_verb)
    )


def _preview_command(family: str, command: str) -> Any:
    def invoke(ctx: typer.Context) -> None:
        state = require_state(ctx)
        try:
            positionals, _, _ = _parsed(ctx)
            service = getattr(state.client(), family.replace("-", "_"))
            if command in {"list", "top"}:
                result = service.list()
            elif command == "show":
                result = service.show(int(positionals[0]))
            else:
                result = service.instantiate(
                    int(positionals[0]),
                    _json_file(positionals[1] if len(positionals) > 1 else None),
                )
            state.render(result, resource=family)
        except Exception as exc:
            raise_cli_error(exc)

    invoke.__name__ = f"{family.replace('-', '_')}_{command.replace('-', '_')}"
    return invoke


for _family, _app in (
    ("provider-template", provider_template_app),
    ("provision-template", provision_template_app),
):
    for _verb in ("list", "show", "top", "instantiate"):
        _app.command(_verb, context_settings=COMMAND_CONTEXT)(_preview_command(_family, _verb))
