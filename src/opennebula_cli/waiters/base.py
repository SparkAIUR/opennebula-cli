"""Waiter primitives."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


Predicate = Callable[[T], bool]
StateGetter = Callable[[int], T]


class WaitEvent(BaseModel):
    """Single waiter poll event."""

    model_config = ConfigDict(frozen=True)

    resource: str
    id: int
    state: str
