"""Command lock enforcement helpers."""

from __future__ import annotations

from dataclasses import dataclass

from opennebula_cli.state_store import StateStore


@dataclass(slots=True, frozen=True)
class Invocation:
    """Parsed command invocation."""

    command: str | None
    action: str | None


GLOBAL_OPTIONS_WITH_VALUES = {
    "--profile",
    "--endpoint",
    "--auth",
    "--user",
    "--password",
    "--output",
    "--timeout",
    "--cert-dir",
}

GLOBAL_FLAG_OPTIONS = {
    "--no-pager",
    "--no-verify",
    "--verbose",
    "-v",
    "--debug",
}

LIST_ACTION_TOKENS = {"list", "ls", "top"}
SHOW_ACTION_TOKENS = {"show", "info"}
CREATE_ACTION_TOKENS = {
    "create",
    "allocate",
    "register",
    "instantiate",
    "clone",
    "copy",
    "import",
    "init",
}
DELETE_ACTION_TOKENS = {
    "delete",
    "del",
    "rm",
    "remove",
    "purge",
    "terminate",
    "destroy",
}


def parse_invocation(argv: list[str]) -> Invocation:
    """Parse canonical CLI argv into command and action tokens."""

    remainder = list(argv)
    while remainder:
        token = remainder[0]
        if token in GLOBAL_FLAG_OPTIONS:
            remainder.pop(0)
            continue

        option_name, separator, _value = token.partition("=")
        if option_name in GLOBAL_OPTIONS_WITH_VALUES:
            remainder.pop(0)
            if separator:
                continue
            if remainder:
                remainder.pop(0)
            continue
        break

    command = remainder[0] if remainder else None
    action = remainder[1] if len(remainder) > 1 else None
    return Invocation(command=command, action=action)


def normalize_action(token: str | None) -> str:
    """Map a command verb to lock action category."""

    if token is None:
        return "show"
    lowered = token.lower()
    if lowered in LIST_ACTION_TOKENS:
        return "list"
    if lowered in SHOW_ACTION_TOKENS:
        return "show"
    if lowered in CREATE_ACTION_TOKENS:
        return "create"
    if lowered in DELETE_ACTION_TOKENS:
        return "delete"
    return "update"


def ensure_command_allowed(argv: list[str]) -> None:
    """Raise RuntimeError when invocation matches an active lock."""

    parsed = parse_invocation(argv)
    if parsed.command is None:
        return
    command = parsed.command.lower()
    if command == "state":
        return

    lock = StateStore().lock_state()
    if not lock.enabled:
        return

    action = normalize_action(parsed.action)
    command_match = (not lock.commands) or ("all" in lock.commands) or (command in lock.commands)
    action_match = "all" in lock.actions or action in lock.actions
    if not (command_match and action_match):
        return

    raise RuntimeError(
        "Command is locked by local state policy. "
        "Use `one state lock disable` to unlock (password may be required)."
    )
