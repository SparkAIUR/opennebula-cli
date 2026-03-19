"""Live mutation E2E coverage for disposable OpenNebula fixtures."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e]


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


def _run_json(*args: str, env: dict[str, str]) -> object:
    result = _run_cli(*args, env=env)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _find_named_resource_id(family: str, name: str, *, env: dict[str, str]) -> int:
    payload = _run_json("one", "--output", "json", family, "list", env=env)
    assert isinstance(payload, list)
    for item in payload:
        if isinstance(item, dict) and item.get("name") == name and isinstance(item.get("id"), int):
            return int(item["id"])
    pytest.skip(f"No {family} named {name!r} exists in the live environment.")


def _wait_for_vm(vm_id: int, *, env: dict[str, str], timeout: float = 120.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        shown = _run_cli("one", "--output", "json", "vm", "show", str(vm_id), env=env)
        if shown.returncode == 0:
            payload = json.loads(shown.stdout)
            assert isinstance(payload, dict)
            return payload
        time.sleep(2.0)
    pytest.fail(f"VM {vm_id} did not become visible within {timeout} seconds.")


def _wait_for_vm_poweroff_ready(
    vm_id: int,
    *,
    env: dict[str, str],
    timeout: float = 180.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    last_seen: dict[str, object] | None = None
    while time.monotonic() < deadline:
        last_seen = _wait_for_vm(vm_id, env=env, timeout=30.0)
        state = str(last_seen.get("state", "")).upper()
        if state != "PENDING":
            return last_seen
        time.sleep(3.0)
    pytest.fail(f"VM {vm_id} remained PENDING for too long: {last_seen!r}")


def test_template_instantiate_and_poweroff() -> None:
    env = _live_env()
    template_name = os.environ.get("ONE_E2E_TEMPLATE_NAME", "e2e-alpine-lxc")
    vm_prefix = os.environ.get("ONE_E2E_VM_PREFIX", "e2e-vm-")
    template_id = _find_named_resource_id("template", template_name, env=env)
    vm_name = f"{vm_prefix}{int(time.time())}"

    instantiated = _run_json(
        "one",
        "--output",
        "json",
        "template",
        "instantiate",
        str(template_id),
        "--name",
        vm_name,
        env=env,
    )
    assert isinstance(instantiated, dict)
    assert instantiated.get("action") == "instantiate"
    assert instantiated.get("resource") == "vm"
    assert isinstance(instantiated.get("id"), int)
    vm_id = int(instantiated["id"])

    shown = _wait_for_vm(vm_id, env=env)
    assert shown.get("id") == vm_id
    assert shown.get("name") == vm_name
    _wait_for_vm_poweroff_ready(vm_id, env=env)

    powered_off = _run_json(
        "one",
        "--output",
        "json",
        "vm",
        "poweroff",
        str(vm_id),
        "--wait",
        "--timeout",
        "600",
        "--no-progress",
        env=env,
    )
    assert isinstance(powered_off, dict)
    assert powered_off.get("resource") == "vm"
    assert powered_off.get("id") == vm_id
    assert powered_off.get("completed") is True

    final_vm = _run_json("one", "--output", "json", "vm", "show", str(vm_id), env=env)
    assert isinstance(final_vm, dict)
    state = str(final_vm.get("state", "")).upper()
    lcm_state = str(final_vm.get("lcm_state", "")).upper()
    assert "POWEROFF" in state or "POWEROFF" in lcm_state or state in {"DONE", "FAILED"}
