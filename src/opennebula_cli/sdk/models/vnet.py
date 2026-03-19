"""Virtual network models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import normalize_value, object_get


class Vnet(BaseModel):
    """Normalized OpenNebula virtual network model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    type: str | None = None
    bridge: str | None = None
    cluster_id: int | None = None
    template: dict[str, Any] = Field(default_factory=dict)
    reservations: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: object) -> Vnet:
        template = normalize_value(object_get(raw, "TEMPLATE", {}))
        cluster_id = object_get(raw, "CLUSTER_ID")
        reservations = normalize_value(object_get(raw, "AR_POOL", {}))
        normalized_reservations: list[dict[str, Any]]
        if isinstance(reservations, dict) and "AR" in reservations:
            raw_entries = reservations["AR"]
            if isinstance(raw_entries, list):
                normalized_reservations = [
                    entry for entry in raw_entries if isinstance(entry, dict)
                ]
            elif isinstance(raw_entries, dict):
                normalized_reservations = [raw_entries]
            else:
                normalized_reservations = []
        else:
            normalized_reservations = []
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            type=str(object_get(raw, "VN_MAD", object_get(raw, "TYPE", ""))) or None,
            bridge=str(object_get(template, "BRIDGE", "")) or None,
            cluster_id=int(cluster_id) if cluster_id not in (None, "") else None,
            template=template if isinstance(template, dict) else {"value": template},
            reservations=normalized_reservations,
        )
