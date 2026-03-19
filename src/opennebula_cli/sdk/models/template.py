"""Template models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import normalize_value, object_get


class Template(BaseModel):
    """Normalized VM template model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    regtime: int | None = None
    template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Template:
        regtime = object_get(raw, "REGTIME")
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            regtime=int(regtime) if regtime not in (None, "") else None,
            template=normalize_value(object_get(raw, "TEMPLATE", {})),
        )
