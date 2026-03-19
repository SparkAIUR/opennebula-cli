from __future__ import annotations

from pathlib import Path

from tools.check_release_version import expected_tag, normalize_tag, project_version


def test_project_version_reads_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")
    assert project_version(pyproject) == "0.1.0"


def test_normalize_tag_handles_refs() -> None:
    assert normalize_tag("refs/tags/v0.1.0") == "v0.1.0"
    assert normalize_tag("v0.1.0") == "v0.1.0"


def test_expected_tag_matches_version() -> None:
    assert expected_tag("0.1.0") == "v0.1.0"
