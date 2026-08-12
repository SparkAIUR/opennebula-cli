from __future__ import annotations

import json
from collections import deque
from typing import Any

from opennebula_cli.auth.models import ResolvedAuth
from opennebula_cli.config.models import ConnectionSettings, OutputSettings, ResolvedConfig
from opennebula_cli.services.flow import OneFlowService


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class FakeUrlOpen:
    def __init__(self, payloads: list[bytes]) -> None:
        self._payloads: deque[bytes] = deque(payloads)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, request: Any, timeout: float, context: object = None) -> FakeResponse:
        self.calls.append(
            {
                "method": request.get_method(),
                "url": request.full_url,
                "headers": dict(request.headers),
                "timeout": timeout,
                "context": context,
            }
        )
        payload = self._payloads.popleft() if self._payloads else b"{}"
        return FakeResponse(payload)


def _config(*, service_config: dict[str, str] | None = None) -> ResolvedConfig:
    return ResolvedConfig(
        profile=None,
        connection=ConnectionSettings(
            endpoint="http://frontend:2633/RPC2",
            timeout=30.0,
            verify_ssl=True,
            cert_dir=None,
            service_config=service_config or {},
            service_endpoints={"oneflow": "http://frontend:2474"},
        ),
        auth=ResolvedAuth(
            username="oneadmin",
            secret="opennebula",
            source="test",
            raw_session="oneadmin:opennebula",
        ),
        output=OutputSettings(output="json", no_pager=True),
        verbose=0,
        debug=False,
    )


def test_flow_service_uses_oneflow_host_header_from_context_config(monkeypatch: Any) -> None:
    fake = FakeUrlOpen([json.dumps({"DOCUMENT_POOL": {"DOCUMENT": []}}).encode("utf-8")])
    monkeypatch.setattr("opennebula_cli.services.flow.urlopen", fake)

    service = OneFlowService(_config(service_config={"oneflow_host": "localhost"}))
    service.run_official("list", [])

    assert fake.calls
    assert fake.calls[0]["headers"]["Host"] == "localhost"
    assert fake.calls[0]["url"] == "http://frontend:2474/service"


def test_flow_service_normalizes_service_and_role_states(monkeypatch: Any) -> None:
    document = {
        "ID": "7",
        "NAME": "official-name",
        "TEMPLATE": {
            "BODY": {
                "name": "service-name",
                "state": 2,
                "roles": [
                    {"name": "web", "state": 4, "nodes": [{"deploy_id": 42}]},
                    {"name": "future", "state": 99, "nodes": []},
                ],
            }
        },
    }
    fake = FakeUrlOpen([json.dumps({"DOCUMENT_POOL": {"DOCUMENT": document}}).encode("utf-8")])
    monkeypatch.setattr("opennebula_cli.services.flow.urlopen", fake)

    records = OneFlowService(_config()).run_official("list", [])

    assert isinstance(records, list)
    service = records[0]
    assert service.id == 7
    assert (service.state, service.state_id) == ("RUNNING", 2)
    assert (service.roles[0].state, service.roles[0].state_id) == ("WARNING", 4)
    assert service.roles[0].nodes == [{"deploy_id": 42}]
    assert (service.roles[1].state, service.roles[1].state_id) == ("UNKNOWN_99", 99)
    assert service.raw == document
