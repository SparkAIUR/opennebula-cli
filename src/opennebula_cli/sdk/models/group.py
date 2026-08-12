"""Group models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from opennebula_cli.sdk.models.common import object_get


class Group(BaseModel):
    """Normalized group model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str

    @classmethod
    def from_raw(cls, raw: object) -> Group:
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
        )
