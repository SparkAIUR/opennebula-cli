"""Normalized OneFlow service and role models."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import ensure_list, int_or_none, normalize_value

SERVICE_STATES: Final[tuple[str, ...]] = (
    "PENDING",
    "DEPLOYING",
    "RUNNING",
    "UNDEPLOYING",
    "WARNING",
    "DONE",
    "FAILED_UNDEPLOYING",
    "FAILED_DEPLOYING",
    "SCALING",
    "FAILED_SCALING",
    "COOLDOWN",
    "DEPLOYING_NETS",
    "UNDEPLOYING_NETS",
    "FAILED_DEPLOYING_NETS",
    "FAILED_UNDEPLOYING_NETS",
    "HOLD",
)

ROLE_STATES: Final[tuple[str, ...]] = SERVICE_STATES[:11] + ("HOLD",)


def _state_pair(value: object, states: tuple[str, ...]) -> tuple[str, int | None]:
    state_id = int_or_none(value)
    if state_id is not None:
        if 0 <= state_id < len(states):
            return states[state_id], state_id
        return f"UNKNOWN_{state_id}", state_id
    if value in (None, ""):
        return "", None
    label = str(value).upper()
    try:
        return label, states.index(label)
    except ValueError:
        return label, None


def _document_body(document: Mapping[str, object]) -> dict[str, Any]:
    template = document.get("TEMPLATE", document.get("template"))
    body: object = template
    if isinstance(template, Mapping):
        body = template.get("BODY", template.get("body", template))
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return {}
    normalized = normalize_value(body)
    return dict(normalized) if isinstance(normalized, Mapping) else {}


class OneFlowRole(BaseModel):
    """Stable OneFlow role view with versioned state identity and node membership."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    state: str
    state_id: int | None = None
    nodes: list[Any] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, value: object) -> OneFlowRole:
        normalized = normalize_value(value)
        raw = dict(normalized) if isinstance(normalized, Mapping) else {"value": normalized}
        state, state_id = _state_pair(raw.get("state", raw.get("STATE")), ROLE_STATES)
        name = raw.get("name", raw.get("NAME"))
        return cls(
            name=str(name) if name is not None else None,
            state=state,
            state_id=state_id,
            nodes=[
                normalize_value(node) for node in ensure_list(raw.get("nodes", raw.get("NODES")))
            ],
            raw=raw,
        )


class OneFlowServiceDocument(BaseModel):
    """Stable OneFlow service view retaining the complete official document."""

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    name: str | None = None
    state: str
    state_id: int | None = None
    roles: list[OneFlowRole] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, value: object) -> OneFlowServiceDocument:
        normalized = normalize_value(value)
        raw = dict(normalized) if isinstance(normalized, Mapping) else {"value": normalized}
        body = _document_body(raw)
        state, state_id = _state_pair(
            body.get("state", raw.get("STATE", raw.get("state"))),
            SERVICE_STATES,
        )
        name = body.get("name", raw.get("NAME", raw.get("name")))
        roles = ensure_list(body.get("roles", body.get("ROLES")))
        return cls(
            id=int_or_none(raw.get("ID", raw.get("id"))),
            name=str(name) if name is not None else None,
            state=state,
            state_id=state_id,
            roles=[OneFlowRole.from_raw(role) for role in roles],
            raw=raw,
        )
