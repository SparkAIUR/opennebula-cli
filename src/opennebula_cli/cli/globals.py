"""Shared CLI constants."""

from __future__ import annotations

from enum import StrEnum


class OutputMode(StrEnum):
    TABLE = "table"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    CSV = "csv"
    RAW = "raw"


MACHINE_OUTPUTS: set[OutputMode] = {
    OutputMode.JSON,
    OutputMode.YAML,
    OutputMode.XML,
    OutputMode.CSV,
    OutputMode.RAW,
}
