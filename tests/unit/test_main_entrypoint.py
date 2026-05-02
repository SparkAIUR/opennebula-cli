from __future__ import annotations

import pytest

from opennebula_cli.__main__ import _normalize_root_output_argv


def test_normalize_root_output_argv_hoists_split_form() -> None:
    normalized = _normalize_root_output_argv(["vm", "show", "42", "--output", "json"])

    assert normalized == ["--output", "json", "vm", "show", "42"]


def test_normalize_root_output_argv_hoists_equals_form() -> None:
    normalized = _normalize_root_output_argv(["vm", "show", "42", "--output=json"])

    assert normalized == ["--output=json", "vm", "show", "42"]


def test_normalize_root_output_argv_prefers_last_output_option() -> None:
    normalized = _normalize_root_output_argv([
        "--output",
        "yaml",
        "vm",
        "show",
        "42",
        "--output",
        "json",
    ])

    assert normalized == ["--output", "json", "vm", "show", "42"]


def test_normalize_root_output_argv_requires_output_value() -> None:
    with pytest.raises(SystemExit, match="Missing value for global option: --output"):
        _normalize_root_output_argv(["vm", "show", "42", "--output"])

