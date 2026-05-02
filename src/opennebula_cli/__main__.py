"""Console entrypoint."""

from __future__ import annotations

import sys

from opennebula_cli.cli.app import app

__all__ = ["main"]


def _normalize_root_output_argv(argv: list[str]) -> list[str]:
    """Hoist --output global option so users can place it after subcommands."""

    normalized: list[str] = []
    output_tokens: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--output":
            if index + 1 >= len(argv):
                raise SystemExit("Missing value for global option: --output")
            output_tokens = ["--output", argv[index + 1]]
            index += 2
            continue
        if token.startswith("--output="):
            output_tokens = [token]
            index += 1
            continue
        normalized.append(token)
        index += 1
    return [*output_tokens, *normalized]


def main() -> None:
    """Run the Typer application."""
    sys.argv = [sys.argv[0], *_normalize_root_output_argv(sys.argv[1:])]
    app()


if __name__ == "__main__":
    main()
