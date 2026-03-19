from __future__ import annotations

from opennebula_cli.sdk.models.vm import Vm


def test_vm_from_raw_maps_numeric_state_codes() -> None:
    vm = Vm.from_raw(
        {
            "ID": 5,
            "NAME": "e2e-vm",
            "STATE": 8,
            "LCM_STATE": 0,
            "TEMPLATE": {"NIC": {"IP": "172.20.10.10"}},
        }
    )

    assert vm.state == "POWEROFF"
    assert vm.lcm_state == "LCM_INIT"
    assert vm.ips == ["172.20.10.10"]
