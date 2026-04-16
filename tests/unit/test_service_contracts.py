from __future__ import annotations

from typing import Any

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.sdk.models.common import Ack, normalize_value
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
