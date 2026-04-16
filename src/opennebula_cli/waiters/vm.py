"""VM-specific wait predicates."""

from __future__ import annotations

from opennebula_cli.sdk.models.vm import Vm


def is_powered_off(vm: Vm) -> bool:
    """Return true when a VM is considered powered off."""

    state = vm.state.upper()
    lcm = (vm.lcm_state or "").upper()
    return "POWEROFF" in state or "POWEROFF" in lcm or state in {"DONE", "FAILED"}


def is_running(vm: Vm) -> bool:
    """Return true when a VM is considered running."""

    state = vm.state.upper()
    lcm = (vm.lcm_state or "").upper()
    return state == "ACTIVE" and lcm == "RUNNING"
