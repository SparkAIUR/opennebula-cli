"""Normalized OneForm models that retain complete backend documents."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import int_or_none, normalize_value

PROVISION_STATES = (
    "PENDING",
    "INIT",
    "PLANNING",
    "APPLYING",
    "CONFIGURING_PROVISION",
    "CONFIGURING_ONE",
    "RUNNING",
    "SCALING",
    "DEPROVISIONING_ONE",
    "DEPROVISIONING",
    "DONE",
    "INIT_FAILURE",
    "PLANNING_FAILURE",
    "APPLYING_FAILURE",
    "CONFIGURING_PROVISION_FAILURE",
    "CONFIGURING_ONE_FAILURE",
    "SCALING_FAILURE",
    "DEPROVISIONING_ONE_FAILURE",
    "DEPROVISIONING_FAILURE",
    "DONE_FAILURE",
)


def _mapping(value: object) -> dict[str, Any]:
    normalized = normalize_value(value)
    return dict(normalized) if isinstance(normalized, Mapping) else {}


def _body(document: Mapping[str, object]) -> dict[str, Any]:
    template = document.get("TEMPLATE", document.get("template"))
    if not isinstance(template, Mapping):
        return {}
    for key in ("PROVISION_BODY", "PROVIDER_BODY", "BODY", "body"):
        candidate = template.get(key)
        if isinstance(candidate, str):
            try:
                candidate = json.loads(candidate)
            except json.JSONDecodeError:
                continue
        if isinstance(candidate, Mapping):
            return _mapping(candidate)
    return {}


def _state_pair(value: object, states: tuple[str, ...] | None) -> tuple[str | None, int | None]:
    state_id = int_or_none(value)
    if state_id is not None:
        if states is not None and 0 <= state_id < len(states):
            return states[state_id], state_id
        return f"UNKNOWN_{state_id}", state_id
    if value in (None, ""):
        return None, None
    label = str(value).upper()
    if states is not None:
        try:
            return label, states.index(label)
        except ValueError:
            pass
    return label, None


class OneFormDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | str | None = None
    name: str | None = None
    state: str | None = None
    state_id: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(
        cls,
        value: object,
        *,
        state_labels: tuple[str, ...] | None = None,
    ) -> OneFormDocument:
        raw = _mapping(value)
        document_value = raw.get("DOCUMENT", raw.get("document", raw))
        document = _mapping(document_value)
        body = _body(document)
        identifier = document.get("ID", document.get("id", raw.get("ID", raw.get("id"))))
        state_value = body.get(
            "state",
            document.get("STATE", document.get("state", raw.get("STATE", raw.get("state")))),
        )
        state, state_id = _state_pair(state_value, state_labels)
        name = body.get(
            "name",
            document.get("NAME", document.get("name", raw.get("NAME", raw.get("name")))),
        )
        numeric_identifier = int_or_none(identifier)
        return cls(
            id=(
                numeric_identifier
                if numeric_identifier is not None
                else (identifier if isinstance(identifier, str) else None)
            ),
            name=str(name) if name is not None else None,
            state=state,
            state_id=state_id,
            raw=raw,
        )
