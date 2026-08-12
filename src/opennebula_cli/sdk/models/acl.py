"""ACL models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from opennebula_cli.sdk.models.common import object_get


class AclRule(BaseModel):
    """Normalized ACL rule model."""

    model_config = ConfigDict(frozen=True)

    id: int
    user: str | None = None
    resource: str | None = None
    rights: str | None = None

    @classmethod
    def from_raw(cls, raw: object) -> AclRule:
        return cls(
            id=int(object_get(raw, "ID", 0)),
            user=str(object_get(raw, "USER", "")) or None,
            resource=str(object_get(raw, "RESOURCE", "")) or None,
            rights=str(object_get(raw, "RIGHTS", "")) or None,
        )
