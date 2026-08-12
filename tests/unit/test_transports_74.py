from __future__ import annotations

from typing import Any

import pytest

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.transports.policy import PolicyTransport
from opennebula_cli.transports.routing import RoutingTransport
from opennebula_cli.transports.xmlrpc_raw import RawXmlRpcTransport


class FakeServer:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def __getattr__(self, method: str) -> Any:
        def call(*args: object) -> object:
            self.calls.append((method, args))
            return self.response

        return call


def raw_transport(response: object) -> tuple[RawXmlRpcTransport, FakeServer]:
    transport = RawXmlRpcTransport.__new__(RawXmlRpcTransport)
    server = FakeServer(response)
    transport._session = "secret-session"  # noqa: SLF001
    transport._server = server  # noqa: SLF001
    return transport, server


@pytest.mark.parametrize(
    "method,args",
    [
        ("one.datastore.info", (126,)),
        ("one.vmpool.infoextended", (-2, -1, -1, -1)),
        ("one.template.info", (24,)),
        ("one.system.version", ()),
    ],
)
def test_raw_transport_preserves_complete_wire_method(
    method: str, args: tuple[object, ...]
) -> None:
    transport, server = raw_transport([True, "ok", 0])

    assert transport.call(method, *args) == "ok"
    assert server.calls == [(method, ("secret-session", *args))]


def test_raw_transport_materializes_repeated_xml_vectors() -> None:
    xml = (
        "<VM_POOL><VM><ID>1</ID><TEMPLATE><NIC><IP>10.0.0.1</IP></NIC>"
        "<NIC><IP>10.0.0.2</IP></NIC></TEMPLATE></VM>"
        "<VM><ID>2</ID></VM></VM_POOL>"
    )
    transport, _ = raw_transport([True, xml, 0])

    assert transport.call("one.vmpool.infoextended", -2, -1, -1, -1) == {
        "VM": [
            {
                "ID": "1",
                "TEMPLATE": {"NIC": [{"IP": "10.0.0.1"}, {"IP": "10.0.0.2"}]},
            },
            {"ID": "2"},
        ]
    }
    assert transport.call_raw("one.vmpool.infoextended", -2, -1, -1, -1) == xml


def test_policy_transport_preserves_literal_read_payload() -> None:
    class LiteralTransport:
        name = "raw"

        def supports(self, _method: str) -> bool:
            return True

        def call(self, _method: str, *_args: object) -> object:
            return {"parsed": True}

        def call_raw(self, _method: str, *_args: object) -> object:
            return "<VM_POOL/>"

    transport = PolicyTransport(LiteralTransport(), context="locked")  # type: ignore[arg-type]
    assert transport.call_raw("one.vmpool.info", -2, -1, -1, -1) == "<VM_POOL/>"


class FakePyone:
    name = "pyone"

    def supports(self, method: str) -> bool:
        return True

    def call(self, method: str, *args: object) -> object:
        raise ApiError("submitted but failed")


class FakeRaw:
    name = "raw"

    def __init__(self) -> None:
        self.called = False

    def supports(self, method: str) -> bool:
        return True

    def call(self, method: str, *args: object) -> object:
        self.called = True
        return True


def test_auto_transport_never_replays_after_request_failure() -> None:
    raw = FakeRaw()
    routing = RoutingTransport(FakePyone(), raw)  # type: ignore[arg-type]

    with pytest.raises(ApiError):
        routing.call("one.vm.delete", 9)

    assert raw.called is False
