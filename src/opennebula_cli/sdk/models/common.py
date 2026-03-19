"""Common SDK models and helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def object_get(raw: object, key: str, default: Any = None) -> Any:
    """Get a field from a mapping-like or object-like backend response."""

    if isinstance(raw, Mapping):
        return raw.get(key, default)
    return getattr(raw, key, default)


def ensure_list(value: object) -> list[object]:
    """Normalize a scalar or iterable response field to a list."""

    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return list(value)
    return [value]


def normalize_mapping(raw: object) -> dict[str, Any]:
    """Recursively normalize a backend object to plain Python structures."""

    if isinstance(raw, BaseModel):
        return raw.model_dump(mode="json")
    if isinstance(raw, Mapping):
        return {str(key): normalize_value(value) for key, value in raw.items()}
    if hasattr(raw, "__dict__"):
        return {
            key: normalize_value(value)
            for key, value in vars(raw).items()
            if not key.startswith("_")
        }
    return {"value": raw}


def normalize_value(raw: object) -> Any:
    """Recursively normalize arbitrary backend values."""

    if isinstance(raw, BaseModel):
        return raw.model_dump(mode="json")
    if isinstance(raw, Mapping):
        return {str(key): normalize_value(value) for key, value in raw.items()}
    if isinstance(raw, list):
        return [normalize_value(item) for item in raw]
    if isinstance(raw, tuple):
        return [normalize_value(item) for item in raw]
    if hasattr(raw, "__dict__"):
        return normalize_mapping(raw)
    return raw


class Ack(BaseModel):
    """Summary for a mutating action that returned immediately."""

    model_config = ConfigDict(frozen=True)

    resource: str
    id: int
    action: str
    message: str | None = None


class WaitSpec(BaseModel):
    """Waiter settings."""

    model_config = ConfigDict(frozen=True)

    timeout: float = 300.0
    poll_interval: float = 2.0
    show_progress: bool = True


class WaitResult(BaseModel):
    """Result of a waiter operation."""

    model_config = ConfigDict(frozen=True)

    resource: str
    id: int
    state: str
    completed: bool = True
    detail: dict[str, Any] = Field(default_factory=dict)
