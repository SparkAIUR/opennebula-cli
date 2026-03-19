"""Host models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import normalize_value, object_get


class Host(BaseModel):
    """Normalized host model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    state: str
    cluster: str | None = None
    host_share: dict[str, Any] = Field(default_factory=dict)
    template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Host:
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            state=str(object_get(raw, "STATE_STR", object_get(raw, "STATE", ""))),
            cluster=str(object_get(raw, "CLUSTER", "")) or None,
            host_share=normalize_value(object_get(raw, "HOST_SHARE", {})),
            template=normalize_value(object_get(raw, "TEMPLATE", {})),
        )
