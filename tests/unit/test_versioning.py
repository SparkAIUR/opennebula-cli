from __future__ import annotations

import subprocess
from importlib.metadata import PackageNotFoundError

from opennebula_cli.versioning import app_version, git_hash


def test_app_version_uses_importlib_metadata(monkeypatch) -> None:
    monkeypatch.setattr("opennebula_cli.versioning.version", lambda _name: "7.1.0")

    assert app_version() == "7.1.0"


def test_app_version_falls_back_to_source_version(monkeypatch) -> None:
    def _raise(_: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr("opennebula_cli.versioning.version", _raise)
    monkeypatch.setattr("opennebula_cli.versioning.__version__", "7.0.1")

    assert app_version() == "7.0.1"


def test_git_hash_prefers_stamped_build_value(monkeypatch) -> None:
    monkeypatch.setattr("opennebula_cli.versioning.BUILD_GIT_HASH", "abc123def456")

    assert git_hash() == "abc123def456"


def test_git_hash_falls_back_to_local_git(monkeypatch) -> None:
    monkeypatch.setattr("opennebula_cli.versioning.BUILD_GIT_HASH", "unknown")

    class _Completed:
        stdout = "deadbee\n"

    def _run(*_args, **_kwargs):
        return _Completed()

    monkeypatch.setattr("opennebula_cli.versioning.subprocess.run", _run)

    assert git_hash() == "deadbee"


def test_git_hash_returns_unknown_when_git_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("opennebula_cli.versioning.BUILD_GIT_HASH", "unknown")

    def _run(*_args, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="git")

    monkeypatch.setattr("opennebula_cli.versioning.subprocess.run", _run)

    assert git_hash() == "unknown"
