"""Raw XML-RPC models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class RawCallResult(BaseModel):
    """Result from a guarded raw XML-RPC call."""

    model_config = ConfigDict(frozen=True)

    method: str
    args: list[Any]
    result: Any
