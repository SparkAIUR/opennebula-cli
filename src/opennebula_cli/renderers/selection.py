"""Small, deterministic field-selection helpers shared by all renderers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass

from pydantic import BaseModel

from opennebula_cli.sdk.exceptions import ApiError


def _plain(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value


def field_value(value: object, path: str) -> object:
    """Resolve a dotted mapping/list field path with case-insensitive keys."""

    current = _plain(value)
    for component in path.split("."):
        if isinstance(current, Mapping):
            matching = next(
                (key for key in current if str(key).casefold() == component.casefold()), None
            )
            if matching is None:
                raise ApiError(f"Field path not found: {path}")
            current = _plain(current[matching])
            continue
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            try:
                current = _plain(current[int(component)])
            except (ValueError, IndexError) as exc:
                raise ApiError(f"Invalid list component in field path: {path}") from exc
            continue
        raise ApiError(f"Field path not found: {path}")
    return current


def transform_output(
    data: object,
    *,
    value_path: str | None,
    select_fields: str | None,
    filter_expression: str | None,
    sort_field: str | None,
) -> object:
    """Apply the intentionally small extraction grammar to renderer input."""

    transformed = _plain(data)
    if filter_expression:
        path, separator, expected = filter_expression.partition("=")
        if not separator or not path:
            raise ApiError("--filter must use path=value syntax")
        if not isinstance(transformed, list):
            raise ApiError("--filter requires list output")
        transformed = [item for item in transformed if str(field_value(item, path)) == expected]
    if sort_field:
        if not isinstance(transformed, list):
            raise ApiError("--sort requires list output")
        transformed = sorted(transformed, key=lambda item: str(field_value(item, sort_field)))
    if select_fields:
        fields = [field.strip() for field in select_fields.split(",") if field.strip()]
        if not fields:
            raise ApiError("--select requires at least one field")

        def select(item: object) -> dict[str, object]:
            return {field: field_value(item, field) for field in fields}

        transformed = (
            [select(item) for item in transformed]
            if isinstance(transformed, list)
            else select(transformed)
        )
    if value_path:
        transformed = field_value(transformed, value_path)
    return transformed
