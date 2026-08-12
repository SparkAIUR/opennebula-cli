"""Shared CLI runtime helpers."""

from __future__ import annotations

from typing import cast

import typer

from opennebula_cli.cli.state import AppState


def require_state(ctx: typer.Context) -> AppState:
    """Return the initialized application state from a Typer context."""

    state = ctx.obj
    if state is None:
        raise RuntimeError("CLI runtime state is not initialized.")
    return cast(AppState, state)
