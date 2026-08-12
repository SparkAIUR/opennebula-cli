"""Public SDK exports without eager imports that create dependency cycles."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opennebula_cli.sdk.client import OneClient

__all__ = ["OneClient"]


def __getattr__(name: str) -> Any:
    if name == "OneClient":
        from opennebula_cli.sdk.client import OneClient

        return OneClient
    raise AttributeError(name)
