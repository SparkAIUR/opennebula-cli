"""User models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from opennebula_cli.sdk.models.common import object_get


class User(BaseModel):
    """Normalized user model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    group: str | None = None
    auth_driver: str | None = None
    enabled: bool | None = None

    @classmethod
    def from_raw(cls, raw: object) -> User:
        enabled_raw = object_get(raw, "ENABLED", None)
        enabled: bool | None = None
        if enabled_raw is not None:
            enabled = str(enabled_raw) in {"1", "true", "True", "YES"}
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            group=str(object_get(raw, "GNAME", "")) or None,
            auth_driver=str(object_get(raw, "AUTH_DRIVER", "")) or None,
            enabled=enabled,
        )
