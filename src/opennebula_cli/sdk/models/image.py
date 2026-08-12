"""Image models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import int_or_none, normalize_value, object_get, state_pair


class Image(BaseModel):
    """Normalized image model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    state: str
    state_id: int | None = None
    type: str | None = None
    datastore_id: int | None = None
    running_vms_count: int | None = None
    source: str | None = None
    path: str | None = None
    template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Image:
        datastore = object_get(raw, "DATASTORE_ID")
        state, state_id = state_pair(raw)
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            state=state,
            state_id=state_id,
            type=str(object_get(raw, "TYPE_STR", object_get(raw, "TYPE", ""))) or None,
            datastore_id=int(datastore) if datastore not in (None, "") else None,
            running_vms_count=int_or_none(object_get(raw, "RUNNING_VMS")),
            source=str(object_get(raw, "SOURCE", "")) or None,
            path=str(object_get(raw, "PATH", "")) or None,
            template=normalize_value(object_get(raw, "TEMPLATE", {})),
        )


class ImageOwnerSummary(BaseModel):
    """Image ownership and attachment summary for recovery triage."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    state: str
    datastore_id: int | None = None
    source: str | None = None
    path: str | None = None
    running_vms: list[int] = Field(default_factory=list)
    vms: list[int] = Field(default_factory=list)
    template: dict[str, Any] = Field(default_factory=dict)
