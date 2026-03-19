"""Datastore models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import normalize_value, object_get


class Datastore(BaseModel):
    """Normalized OpenNebula datastore model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    state: str
    type: str | None = None
    cluster_id: int | None = None
    ds_mad: str | None = None
    tm_mad: str | None = None
    template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Datastore:
        template = normalize_value(object_get(raw, "TEMPLATE", {}))
        cluster_id = object_get(raw, "CLUSTER_ID")
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            state=str(object_get(raw, "STATE_STR", object_get(raw, "STATE", ""))),
            type=str(object_get(raw, "TYPE_STR", object_get(raw, "TYPE", ""))) or None,
            cluster_id=int(cluster_id) if cluster_id not in (None, "") else None,
            ds_mad=str(object_get(template, "DS_MAD", "")) or None,
            tm_mad=str(object_get(template, "TM_MAD", "")) or None,
            template=template if isinstance(template, dict) else {"value": template},
        )
