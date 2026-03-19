"""Common SDK models and helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PYONE_INTERNAL_ATTRS = {
    "custom_attrs",
    "gds_collector_",
    "gds_elementtree_node_",
    "ns_prefix_",
    "original_tagname_",
    "parent_object_",
}


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


def _public_object_items(raw: object) -> list[tuple[str, object]]:
    """Return object items and skip known backend bookkeeping fields."""

    if not hasattr(raw, "__dict__"):
        return []
    return [
        (key, value)
        for key, value in vars(raw).items()
        if not key.startswith("_")
        and not key.endswith("_")
        and not key.endswith("_nsprefix_")
        and key not in PYONE_INTERNAL_ATTRS
    ]


def normalize_mapping(
    raw: object,
    *,
    _seen: set[int] | None = None,
) -> dict[str, Any]:
    """Recursively normalize a backend object to plain Python structures."""

    if isinstance(raw, BaseModel):
        return raw.model_dump(mode="json")

    seen = _seen or set()
    raw_id = id(raw)
    if raw_id in seen:
        return {}

    if isinstance(raw, Mapping):
        seen.add(raw_id)
        try:
            return {
                str(key): normalize_value(value, _seen=seen)
                for key, value in raw.items()
            }
        finally:
            seen.remove(raw_id)

    object_items = _public_object_items(raw)
    if object_items:
        seen.add(raw_id)
        try:
            return {key: normalize_value(value, _seen=seen) for key, value in object_items}
        finally:
            seen.remove(raw_id)

    return {"value": raw}


def normalize_value(raw: object, *, _seen: set[int] | None = None) -> Any:
    """Recursively normalize arbitrary backend values."""

    if isinstance(raw, BaseModel):
        return raw.model_dump(mode="json")
    if raw is None or isinstance(raw, (str, int, float, bool)):
        return raw

    seen = _seen or set()
    raw_id = id(raw)
    if raw_id in seen:
        return None

    if isinstance(raw, Mapping):
        return normalize_mapping(raw, _seen=seen)
    if isinstance(raw, list):
        seen.add(raw_id)
        try:
            return [normalize_value(item, _seen=seen) for item in raw]
        finally:
            seen.remove(raw_id)
    if isinstance(raw, tuple):
        seen.add(raw_id)
        try:
            return [normalize_value(item, _seen=seen) for item in raw]
        finally:
            seen.remove(raw_id)
    if _public_object_items(raw):
        return normalize_mapping(raw, _seen=seen)
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
