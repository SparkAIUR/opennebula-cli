"""Cluster models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import ensure_list, normalize_value, object_get


class Cluster(BaseModel):
    """Normalized OpenNebula cluster model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    hosts: list[int] = Field(default_factory=list)
    datastores: list[int] = Field(default_factory=list)
    vnets: list[int] = Field(default_factory=list)
    template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Cluster:
        host_ids = [int(value) for value in _extract_ids(object_get(raw, "HOSTS"))]
        datastore_ids = [int(value) for value in _extract_ids(object_get(raw, "DATASTORES"))]
        vnet_ids = [int(value) for value in _extract_ids(object_get(raw, "VNETS"))]
        template = normalize_value(object_get(raw, "TEMPLATE", {}))
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            hosts=host_ids,
            datastores=datastore_ids,
            vnets=vnet_ids,
            template=template if isinstance(template, dict) else {"value": template},
        )


def _extract_ids(raw: object) -> list[int]:
    values = object_get(raw, "ID", raw)
    result: list[int] = []
    for value in ensure_list(values):
        if value in (None, ""):
            continue
        if isinstance(value, bool):
            result.append(int(value))
        elif isinstance(value, int):
            result.append(value)
        elif isinstance(value, str):
            result.append(int(value))
    return result
