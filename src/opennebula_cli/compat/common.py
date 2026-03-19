"""Compatibility entrypoint helpers."""

from __future__ import annotations

import sys

from opennebula_cli.cli.app import app

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


def _split_compat_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split leading global options from the compat argv payload."""

    global_args: list[str] = []
    remainder = list(argv)
    while remainder:
        token = remainder[0]
        if token in {"--help", "-h"}:
            break
        if token in GLOBAL_FLAG_OPTIONS:
            global_args.append(remainder.pop(0))
            continue
        option_name, separator, _option_value = token.partition("=")
        if option_name in GLOBAL_OPTIONS_WITH_VALUES:
            global_args.append(remainder.pop(0))
            if separator:
                continue
            if not remainder:
                raise SystemExit(f"Missing value for global option: {option_name}")
            global_args.append(remainder.pop(0))
            continue
        break
    return global_args, remainder


def run_compat(resource: str) -> None:
    """Rewrite argv to the canonical form and execute the Typer app."""

    global_args, remainder = _split_compat_argv(sys.argv[1:])
    sys.argv = ["one", *global_args, resource, *remainder]
    app()
