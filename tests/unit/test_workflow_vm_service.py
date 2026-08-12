from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.sdk.models.common import Ack
from opennebula_cli.sdk.models.vm import Vm
from opennebula_cli.services.workflow_vm import WorkflowVmInitService


@dataclass(slots=True, frozen=True)
class TemplateRecord:
    id: int
    name: str


class StubTemplateService:
    def __init__(
        self,
        *,
        templates: list[TemplateRecord],
        fail_names: set[str] | None = None,
    ) -> None:
        self._templates = templates
        self._fail_names = fail_names or set()
        self.calls: list[tuple[int, str, str | None]] = []
        self._next_id = 100

    def list(self) -> Sequence[TemplateRecord]:
        return self._templates

    def instantiate(
        self,
        template_id: int,
        *,
        name: str | None = None,
        template_body: str | None = None,
    ) -> Ack:
        vm_name = name or ""
        self.calls.append((template_id, vm_name, template_body))
        if vm_name in self._fail_names:
            raise ApiError(f"simulated failure for {vm_name}")
        vm_id = self._next_id
        self._next_id += 1
        return Ack(resource="vm", id=vm_id, action="instantiate")


class StubVmService:
    def __init__(self, states_by_vm: dict[int, list[tuple[str, str | None]]] | None = None) -> None:
        self._states_by_vm = states_by_vm or {}

    def show(self, vm_id: int) -> Vm:
        states = self._states_by_vm.setdefault(vm_id, [("ACTIVE", "RUNNING")])
        if len(states) > 1:
            state, lcm_state = states.pop(0)
        else:
            state, lcm_state = states[0]
        return Vm(
            id=vm_id,
            name=f"vm-{vm_id}",
            state=state,
            lcm_state=lcm_state,
            host=None,
            ips=[],
            template={},
            user_template={},
        )


@pytest.fixture
def template_service() -> StubTemplateService:
    return StubTemplateService(
        templates=[TemplateRecord(id=11, name="base-template")],
        fail_names={"custom-bob"},
    )


@pytest.fixture
def vm_service() -> StubVmService:
    return StubVmService()


def test_apply_bulk_continues_after_failures_and_reports_summary(
    tmp_path: Path,
    template_service: StubTemplateService,
    vm_service: StubVmService,
) -> None:
    workflow = tmp_path / "bulk.yaml"
    workflow.write_text(
        """template:
  name: base-template
global:
  name_prefix: user-vm-
  resources:
    cpu: 2
    vcpu: 4
    ram: 4Gi
    disk: 50Gi
  disks:
    - fstype: ext4
      size: 20Gi
  network:
    - network_name: default
      model: virtio
  context:
    OPENCLAW_MODE: managed
vms:
  - name: alice
  - name: bob
    vm_name: custom-bob
    resources:
      ram: 8Gi
    raw_template:
      MEMORY: 16384
""",
        encoding="utf-8",
    )

    service = WorkflowVmInitService(template_service=template_service, vm_service=vm_service)
    summary = service.apply_bulk(
        workflow,
        set_values=["global.context.OPENCLAW_REGION=us-central"],
    )

    assert summary["total"] == 2
    assert summary["succeeded"] == 1
    assert summary["failed"] == 1
    assert len(summary["results"]) == 2
    assert summary["results"][0]["status"] == "success"
    assert summary["results"][1]["status"] == "failed"
    assert "simulated failure" in str(summary["results"][1]["error"])
    assert len(template_service.calls) == 2

    first_call = template_service.calls[0]
    assert first_call[0] == 11
    assert first_call[1] == "user-vm-alice"
    assert first_call[2] is not None
    assert 'CPU = "2"' in first_call[2]
    assert 'MEMORY = "4096"' in first_call[2]
    assert 'DISK = [ DISK_ID = "0", SIZE = "51200" ]' in first_call[2]
    assert 'DISK = [ FSTYPE = "ext4", SIZE = "20480" ]' in first_call[2]
    assert (
        'CONTEXT = [ OPENCLAW_MODE = "managed", OPENCLAW_REGION = "us-central" ]' in first_call[2]
    )

    second_call = template_service.calls[1]
    assert second_call[1] == "custom-bob"
    assert second_call[2] is not None
    assert 'MEMORY = "16384"' in second_call[2]


def test_init_single_requires_selector_for_multi_entry_file(tmp_path: Path) -> None:
    workflow = tmp_path / "multi.yaml"
    workflow.write_text(
        """template:
  id: 11
vms:
  - name: alice
  - name: bob
""",
        encoding="utf-8",
    )
    service = WorkflowVmInitService(
        template_service=StubTemplateService(
            templates=[TemplateRecord(id=11, name="base-template")]
        ),
        vm_service=StubVmService(),
    )

    with pytest.raises(ApiError, match="selector"):
        service.init_single(
            workflow_file=workflow,
            name=None,
            selector_name=None,
            selector_index=None,
        )


def test_init_single_wait_ready_reaches_active_running(tmp_path: Path) -> None:
    workflow = tmp_path / "single.yaml"
    workflow.write_text(
        """template:
  id: 11
vms:
  - name: alice
""",
        encoding="utf-8",
    )
    template_service = StubTemplateService(templates=[TemplateRecord(id=11, name="base-template")])
    vm_service = StubVmService(states_by_vm={100: [("PENDING", "PROLOG"), ("ACTIVE", "RUNNING")]})
    service = WorkflowVmInitService(template_service=template_service, vm_service=vm_service)

    summary = service.init_single(
        workflow_file=workflow,
        name=None,
        selector_name=None,
        selector_index=None,
        wait_ready=True,
        timeout=5.0,
        poll_interval=0.001,
        show_progress=False,
    )

    assert summary["failed"] == 0
    assert summary["succeeded"] == 1
    assert summary["results"][0]["status"] == "success"
    assert summary["results"][0]["wait_state"] == "ACTIVE/RUNNING"


def test_init_single_without_file_supports_set_overrides() -> None:
    template_service = StubTemplateService(templates=[TemplateRecord(id=11, name="base-template")])
    service = WorkflowVmInitService(
        template_service=template_service,
        vm_service=StubVmService(),
    )

    summary = service.init_single(
        workflow_file=None,
        name="alice",
        selector_name=None,
        selector_index=None,
        template_name="base-template",
        set_values=["global.resources.cpu=3", "global.context.OPENCLAW_USER=alice"],
    )

    assert summary["failed"] == 0
    assert summary["succeeded"] == 1
    assert len(template_service.calls) == 1
    call = template_service.calls[0]
    assert call[1] == "alice"
    assert call[2] is not None
    assert 'CPU = "3"' in call[2]
    assert 'CONTEXT = [ OPENCLAW_USER = "alice" ]' in call[2]
