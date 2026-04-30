from __future__ import annotations

from typing import Any

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.sdk.models.common import Ack, normalize_value
from opennebula_cli.services.image import ImageService
from opennebula_cli.services.raw import RawService
from opennebula_cli.services.template import TemplateService
from opennebula_cli.services.vm import VmService


class StubTransport:
    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def call(self, method: str, *args: object) -> Any:
        self.calls.append((method, args))
        response = self._responses.get(method, {})
        if isinstance(response, list):
            if not response:
                return {}
            next_value = response.pop(0)
            if isinstance(next_value, Exception):
                raise next_value
            return next_value
        if isinstance(response, Exception):
            raise response
        return response


class RecursiveChild:
    def __init__(self, parent: object) -> None:
        self.parent_object_ = parent
        self.VALUE = "ok"
        self.VALUE_nsprefix_ = None


class RecursiveHostShare:
    def __init__(self) -> None:
        self.CPU_USAGE = 0
        self.custom_attrs: dict[str, object] = {}
        self.CHILD = RecursiveChild(self)


def test_normalize_value_skips_pyone_internal_cycles() -> None:
    normalized = normalize_value(RecursiveHostShare())

    assert normalized == {"CPU_USAGE": 0, "CHILD": {"VALUE": "ok"}}


def test_template_service_uses_full_instantiate_signature() -> None:
    transport = StubTransport({"one.template.instantiate": 42})
    service = TemplateService(transport)

    result = service.instantiate(7, name="test-vm")

    assert result.action == "instantiate"
    assert result.resource == "vm"
    assert result.id == 42
    assert transport.calls == [
        ("one.template.instantiate", (7, "test-vm", False, "", False))
    ]


def test_template_service_instantiate_accepts_override_template() -> None:
    transport = StubTransport({"one.template.instantiate": 88})
    service = TemplateService(transport)

    result = service.instantiate(7, name="test-vm", template_body='CPU = "4"')

    assert result.action == "instantiate"
    assert result.resource == "vm"
    assert result.id == 88
    assert transport.calls == [
        ("one.template.instantiate", (7, "test-vm", False, 'CPU = "4"', False))
    ]


def test_template_service_delete_keeps_images_by_default() -> None:
    transport = StubTransport({"one.template.delete": True})
    service = TemplateService(transport)

    result = service.delete(7)

    assert result.action == "delete"
    assert transport.calls == [("one.template.delete", (7, False))]


def test_template_service_create_uses_allocate() -> None:
    transport = StubTransport({"one.template.allocate": 17})
    service = TemplateService(transport)

    result = service.create('NAME = "created-template"')

    assert result.action == "create"
    assert result.resource == "template"
    assert result.id == 17
    assert transport.calls == [("one.template.allocate", ('NAME = "created-template"',))]


def test_vm_poweroff_retries_pending_state() -> None:
    transport = StubTransport(
        {
            "one.vm.action": [
                ApiError(
                    'Error performing action "poweroff": '
                    "This action is not available for state PROLOG"
                ),
                True,
            ]
        }
    )
    service = VmService(transport)

    result = service.poweroff(9, wait=False)

    assert isinstance(result, Ack)
    assert result.action == "poweroff"
    assert transport.calls == [
        ("one.vm.action", ("poweroff", 9)),
        ("one.vm.action", ("poweroff", 9)),
    ]


def test_vm_disk_attach_builds_single_disk_template() -> None:
    transport = StubTransport({"one.vm.attach": True})
    service = VmService(transport)

    result = service.disk_attach(
        9,
        image_id=18,
        dev_prefix="vd",
        target="vdb",
        driver="qcow2",
        cache="writeback",
        readonly=True,
    )

    assert result.action == "disk-attach"
    assert transport.calls == [
        (
            "one.vm.attach",
            (
                9,
                'DISK = [ IMAGE_ID = "18", DEV_PREFIX = "vd", TARGET = "vdb", '
                'DRIVER = "qcow2", CACHE = "writeback", READONLY = "YES" ]',
            ),
        )
    ]


def test_vm_disk_detach_uses_disk_id() -> None:
    transport = StubTransport({"one.vm.detach": True})
    service = VmService(transport)

    result = service.disk_detach(9, disk_id=2)

    assert result.action == "disk-detach"
    assert transport.calls == [("one.vm.detach", (9, 2))]


def test_vm_disk_list_preserves_recovery_fields() -> None:
    transport = StubTransport(
        {
            "one.vm.info": {
                "ID": 9,
                "NAME": "csi-vm",
                "STATE": "3",
                "LCM_STATE": "3",
                "TEMPLATE": {
                    "DISK": {
                        "DISK_ID": "1",
                        "IMAGE_ID": "18",
                        "TARGET": "vdb",
                        "SERIAL": "disk-serial",
                        "DATASTORE_ID": "2",
                        "SOURCE": "/var/lib/one/datastores/2/disk.0",
                    }
                },
            }
        }
    )
    service = VmService(transport)

    disks = service.disk_list(9)

    assert len(disks) == 1
    assert disks[0].disk_id == 1
    assert disks[0].image_id == 18
    assert disks[0].target == "vdb"
    assert disks[0].serial == "disk-serial"
    assert disks[0].raw["SOURCE"] == "/var/lib/one/datastores/2/disk.0"


def test_vm_recover_maps_flags_to_official_operations() -> None:
    transport = StubTransport({"one.vm.recover": True})
    service = VmService(transport)

    service.recover(9, "failure")
    service.recover(9, "success")
    service.recover(9, "retry")
    service.recover(9, "delete")

    assert transport.calls == [
        ("one.vm.recover", (9, 0)),
        ("one.vm.recover", (9, 1)),
        ("one.vm.recover", (9, 2)),
        ("one.vm.recover", (9, 3)),
    ]


def test_vm_lifecycle_action_uses_one_vm_action() -> None:
    transport = StubTransport({"one.vm.action": True})
    service = VmService(transport)

    result = service.action(9, "reboot-hard")

    assert result.action == "reboot-hard"
    assert transport.calls == [("one.vm.action", ("reboot-hard", 9))]


def test_vm_wait_state_matches_state_and_lcm_state() -> None:
    transport = StubTransport(
        {
            "one.vm.info": {
                "ID": 9,
                "NAME": "ready-vm",
                "STATE": "3",
                "LCM_STATE": "3",
            }
        }
    )
    service = VmService(transport)

    result = service.wait_state(
        9,
        state="ACTIVE",
        lcm_state="RUNNING",
        timeout=1,
        poll_interval=0,
        show_progress=False,
    )

    assert result.completed is True
    assert result.state == "ACTIVE/RUNNING"


def test_vm_show_full_preserves_raw_opennebula_fields() -> None:
    transport = StubTransport(
        {
            "one.vm.info": {
                "ID": 9,
                "STATE": "3",
                "LCM_STATE": "17",
                "HISTORY_RECORDS": {"HISTORY": {"HOSTNAME": "host-a"}},
                "USER_TEMPLATE": {"ERROR": "hotplug failed"},
                "TEMPLATE": {"DISK": {"IMAGE_ID": "18", "DISK_ID": "1"}},
            }
        }
    )
    service = VmService(transport)

    full = service.show_full(9)

    assert full["STATE"] == "3"
    assert full["LCM_STATE"] == "17"
    assert full["USER_TEMPLATE"]["ERROR"] == "hotplug failed"
    assert full["TEMPLATE"]["DISK"]["IMAGE_ID"] == "18"


def test_image_show_full_and_owner_preserve_recovery_fields() -> None:
    transport = StubTransport(
        {
            "one.image.info": {
                "ID": "18",
                "NAME": "pvc-image",
                "STATE_STR": "USED",
                "DATASTORE_ID": "2",
                "SOURCE": "/var/lib/one/datastores/2/image",
                "PATH": "/tmp/source.qcow2",
                "RUNNING_VMS": ["9"],
                "VMS": ["9", "10"],
                "TEMPLATE": {"CSI_VOLUME": "pvc-a"},
            }
        }
    )
    service = ImageService(transport)

    full = service.show_full(18)
    owner = service.owner(18)

    assert full["RUNNING_VMS"] == ["9"]
    assert owner.running_vms == [9]
    assert owner.vms == [9, 10]
    assert owner.source == "/var/lib/one/datastores/2/image"
    assert owner.template == {"CSI_VOLUME": "pvc-a"}


def test_raw_service_returns_normalized_result() -> None:
    transport = StubTransport({"one.vm.info": {"ID": "9", "NAME": "raw-vm"}})
    service = RawService(transport)

    result = service.call("one.vm.info", [9])

    assert result.method == "one.vm.info"
    assert result.args == [9]
    assert result.result == {"ID": "9", "NAME": "raw-vm"}
    assert transport.calls == [("one.vm.info", (9,))]
