"""Live E2E coverage for a disposable OpenNebula deployment."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e]

FAMILIES: tuple[str, ...] = (
    "vm",
    "host",
    "image",
    "template",
    "vnet",
    "datastore",
    "cluster",
)


def _live_env() -> dict[str, str]:
    endpoint = os.environ.get("ONE_XMLRPC")
    auth_path = os.environ.get("ONE_AUTH")
    if not endpoint or not auth_path:
        pytest.skip("ONE_XMLRPC and ONE_AUTH must be set for live E2E tests.")
    if not Path(auth_path).exists():
        pytest.skip(f"ONE_AUTH path does not exist: {auth_path}")
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    env.setdefault("TERM", "dumb")
    return env


def _run_cli(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", *args],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )


def _observed_ids(payload: object) -> list[int]:
    if not isinstance(payload, list):
        return []
    ids: list[int] = []
    for item in payload:
        if isinstance(item, dict) and isinstance(item.get("id"), int):
            ids.append(item["id"])
    return ids


@pytest.mark.parametrize("family", FAMILIES)
def test_family_help(family: str) -> None:
    env = _live_env()
    result = _run_cli("one", family, "--help", env=env)
    assert result.returncode == 0, result.stderr
    assert f"Usage: one {family}" in result.stdout


@pytest.mark.parametrize("family", FAMILIES)
def test_compat_help(family: str) -> None:
    env = _live_env()
    result = _run_cli(f"one{family}", "list", "--help", env=env)
    assert result.returncode == 0, result.stderr
    assert "Examples:" in result.stdout


@pytest.mark.parametrize("family", FAMILIES)
def test_list_json(family: str) -> None:
    env = _live_env()
    result = _run_cli("one", "--output", "json", family, "list", env=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)


@pytest.mark.parametrize("family", FAMILIES)
def test_show_json_when_resource_exists(family: str) -> None:
    env = _live_env()
    listed = _run_cli("one", "--output", "json", family, "list", env=env)
    assert listed.returncode == 0, listed.stderr
    ids = _observed_ids(json.loads(listed.stdout))
    if not ids:
        pytest.skip(f"No {family} resources exist in the live environment.")

    shown = _run_cli("one", "--output", "json", family, "show", str(ids[0]), env=env)
    assert shown.returncode == 0, shown.stderr
    detail = json.loads(shown.stdout)
    assert isinstance(detail, dict)
    assert detail.get("id") == ids[0]
