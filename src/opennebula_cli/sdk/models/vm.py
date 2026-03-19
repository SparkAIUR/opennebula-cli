"""VM models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import normalize_value, object_get


class Vm(BaseModel):
    """Normalized OpenNebula VM model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    state: str
    lcm_state: str | None = None
    host: str | None = None
    ips: list[str] = Field(default_factory=list)
    template: dict[str, Any] = Field(default_factory=dict)
    user_template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Vm:
        template = normalize_value(object_get(raw, "TEMPLATE", {}))
        user_template = normalize_value(object_get(raw, "USER_TEMPLATE", {}))
        history = object_get(raw, "HISTORY_RECORDS")
        ips: list[str] = []
        if isinstance(template, dict):
            nic = template.get("NIC")
            if isinstance(nic, list):
                ips = [
                    str(item.get("IP"))
                    for item in nic
                    if isinstance(item, dict) and item.get("IP")
                ]
            elif isinstance(nic, dict) and nic.get("IP"):
                ips = [str(nic["IP"])]
        lcm_state = str(
            object_get(raw, "LCM_STATE_STR", object_get(raw, "LCM_STATE", ""))
        ) or None
        host = (
            str(object_get(history, "HOSTNAME", object_get(raw, "HISTORY", None)))
            if history
            else None
        )
        normalized_template = template if isinstance(template, dict) else {"value": template}
        normalized_user_template = (
            user_template if isinstance(user_template, dict) else {"value": user_template}
        )
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            state=str(object_get(raw, "STATE_STR", object_get(raw, "STATE", ""))),
            lcm_state=lcm_state,
            host=host,
            ips=ips,
            template=normalized_template,
            user_template=normalized_user_template,
        )
