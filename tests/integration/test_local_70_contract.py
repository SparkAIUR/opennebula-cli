from __future__ import annotations

from threading import Thread
from xmlrpc.server import SimpleXMLRPCServer

import pytest

from opennebula_cli.auth.models import ResolvedAuth
from opennebula_cli.config.models import ConnectionSettings, ResolvedConfig
from opennebula_cli.sdk.client import OneClient
from opennebula_cli.sdk.exceptions import UnsupportedCapabilityError

VM_XML = """<VM><ID>7</ID><NAME>e2e-70-vm</NAME><STATE>3</STATE><LCM_STATE>3</LCM_STATE>
<TEMPLATE><NIC><IP>192.0.2.7</IP></NIC></TEMPLATE><USER_TEMPLATE/></VM>"""
POOL_XML = f"<VM_POOL>{VM_XML}</VM_POOL>"


@pytest.fixture
def opennebula_70_endpoint() -> str:
    server = SimpleXMLRPCServer(("127.0.0.1", 0), logRequests=False, allow_none=True)
    server.register_function(lambda _session: [True, "7.0.2", 0], "one.system.version")
    server.register_function(
        lambda _session, _filter, _start, _end, _state: [True, POOL_XML, 0],
        "one.vmpool.infoextended",
    )
    server.register_function(lambda _session, _vm_id: [True, VM_XML, 0], "one.vm.info")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def config(endpoint: str) -> ResolvedConfig:
    return ResolvedConfig(
        context_name="local-7.0",
        connection=ConnectionSettings(endpoint=endpoint),
        auth=ResolvedAuth(
            username="oneadmin",
            secret="test-only",
            source="test",
            raw_session="oneadmin:test-only",
        ),
    )


@pytest.mark.parametrize("backend", ["pyone", "raw"])
def test_previous_server_line_works_with_both_backends(
    opennebula_70_endpoint: str, backend: str
) -> None:
    client = OneClient.from_config(config(opennebula_70_endpoint), backend=backend)

    assert client.server_info().profile == "7.0"
    assert client.vm.list()[0].state == "ACTIVE"
    assert client.vm.show(7).lcm_state == "RUNNING"
    with pytest.raises(UnsupportedCapabilityError):
        client.require_capability("one.vm.exec")
