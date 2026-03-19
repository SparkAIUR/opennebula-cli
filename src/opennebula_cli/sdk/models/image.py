"""Image models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import normalize_value, object_get


class Image(BaseModel):
    """Normalized image model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    state: str
    type: str | None = None
    datastore_id: int | None = None
    template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Image:
        datastore = object_get(raw, "DATASTORE_ID")
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            state=str(object_get(raw, "STATE_STR", object_get(raw, "STATE", ""))),
            type=str(object_get(raw, "TYPE_STR", object_get(raw, "TYPE", ""))) or None,
            datastore_id=int(datastore) if datastore not in (None, "") else None,
            template=normalize_value(object_get(raw, "TEMPLATE", {})),
        )
