"""Datastore models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import (
    ensure_list,
    int_or_none,
    normalize_value,
    object_get,
    state_pair,
)


def _int_values(value: object) -> list[int]:
    result: list[int] = []
    for item in ensure_list(value):
        parsed = int_or_none(item)
        if parsed is not None:
            result.append(parsed)
    return result


class Datastore(BaseModel):
    """Normalized OpenNebula datastore model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    state: str
    state_id: int | None = None
    type: str | None = None
    cluster_id: int | None = None
    ds_mad: str | None = None
    tm_mad: str | None = None
    total_mb: int | None = None
    free_mb: int | None = None
    used_mb: int | None = None
    permissions: dict[str, Any] = Field(default_factory=dict)
    clusters: list[int] = Field(default_factory=list)
    images: list[int] = Field(default_factory=list)
    template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Datastore:
        template = normalize_value(object_get(raw, "TEMPLATE", {}))
        cluster_id = object_get(raw, "CLUSTER_ID")
        state, state_id = state_pair(raw)
        cluster_values = ensure_list(object_get(object_get(raw, "CLUSTERS", {}), "ID"))
        image_values = ensure_list(object_get(object_get(raw, "IMAGES", {}), "ID"))
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            state=state,
            state_id=state_id,
            type=str(object_get(raw, "TYPE_STR", object_get(raw, "TYPE", ""))) or None,
            cluster_id=int(cluster_id) if cluster_id not in (None, "") else None,
            ds_mad=str(object_get(template, "DS_MAD", "")) or None,
            tm_mad=str(object_get(template, "TM_MAD", "")) or None,
            total_mb=int_or_none(object_get(raw, "TOTAL_MB")),
            free_mb=int_or_none(object_get(raw, "FREE_MB")),
            used_mb=int_or_none(object_get(raw, "USED_MB")),
            permissions=normalize_value(object_get(raw, "PERMISSIONS", {})),
            clusters=_int_values(cluster_values),
            images=_int_values(image_values),
            template=template if isinstance(template, dict) else {"value": template},
        )
