"""Console entrypoint."""

from __future__ import annotations

from opennebula_cli.cli.app import app

__all__ = ["main"]


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
