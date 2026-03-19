"""View definitions for human list rendering."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ColumnSpec(BaseModel):
    """Column definition used by human list renderers."""

    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    justify: Literal["left", "right", "center", "full", "default"] = "left"


class ViewSpec(BaseModel):
    """Simple named view."""

    model_config = ConfigDict(frozen=True)

    name: str
    columns: list[ColumnSpec] = Field(default_factory=list)


DEFAULT_VIEWS: dict[str, ViewSpec] = {
    "vm": ViewSpec(
        name="vm",
        columns=[
            ColumnSpec(key="id", label="ID", justify="right"),
            ColumnSpec(key="name", label="NAME"),
            ColumnSpec(key="state", label="STATE"),
            ColumnSpec(key="host", label="HOST"),
        ],
    ),
    "host": ViewSpec(
        name="host",
        columns=[
            ColumnSpec(key="id", label="ID", justify="right"),
            ColumnSpec(key="name", label="NAME"),
            ColumnSpec(key="state", label="STATE"),
            ColumnSpec(key="cluster", label="CLUSTER"),
        ],
    ),
    "image": ViewSpec(
        name="image",
        columns=[
            ColumnSpec(key="id", label="ID", justify="right"),
            ColumnSpec(key="name", label="NAME"),
            ColumnSpec(key="state", label="STATE"),
            ColumnSpec(key="type", label="TYPE"),
        ],
    ),
    "template": ViewSpec(
        name="template",
        columns=[
            ColumnSpec(key="id", label="ID", justify="right"),
            ColumnSpec(key="name", label="NAME"),
            ColumnSpec(key="regtime", label="REGTIME"),
        ],
    ),
    "vnet": ViewSpec(
        name="vnet",
        columns=[
            ColumnSpec(key="id", label="ID", justify="right"),
            ColumnSpec(key="name", label="NAME"),
            ColumnSpec(key="type", label="TYPE"),
            ColumnSpec(key="bridge", label="BRIDGE"),
        ],
    ),
    "datastore": ViewSpec(
        name="datastore",
        columns=[
            ColumnSpec(key="id", label="ID", justify="right"),
            ColumnSpec(key="name", label="NAME"),
            ColumnSpec(key="state", label="STATE"),
            ColumnSpec(key="type", label="TYPE"),
        ],
    ),
    "cluster": ViewSpec(
        name="cluster",
        columns=[
            ColumnSpec(key="id", label="ID", justify="right"),
            ColumnSpec(key="name", label="NAME"),
            ColumnSpec(key="hosts", label="HOSTS"),
            ColumnSpec(key="datastores", label="DATASTORES"),
        ],
    ),
}
