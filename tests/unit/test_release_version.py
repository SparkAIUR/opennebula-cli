from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_release_helper() -> ModuleType:
    module_path = Path(__file__).resolve().parents[2] / "tools" / "check_release_version.py"
    spec = importlib.util.spec_from_file_location("check_release_version", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load tools/check_release_version.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_project_version_reads_pyproject(tmp_path: Path) -> None:
    helper = load_release_helper()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")
    assert helper.project_version(pyproject) == "0.1.0"


def test_normalize_tag_handles_refs() -> None:
    helper = load_release_helper()
    assert helper.normalize_tag("refs/tags/v0.1.0") == "v0.1.0"
    assert helper.normalize_tag("v0.1.0") == "v0.1.0"


def test_expected_tag_matches_version() -> None:
    helper = load_release_helper()
    assert helper.expected_tag("0.1.0") == "v0.1.0"
