from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from opennebula_cli.auth.models import ResolvedAuth
from opennebula_cli.config.models import ConnectionSettings, OutputSettings, ResolvedConfig
from opennebula_cli.sdk.models.common import Ack
from opennebula_cli.services.flow_template import OneFlowTemplateService


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
                "data": request.data,
                "headers": dict(request.headers),
                "timeout": timeout,
                "context": context,
            }
        )
        payload = self._payloads.popleft() if self._payloads else b"{}"
        return FakeResponse(payload)


def _config(endpoint: str = "http://frontend:2633/RPC2") -> ResolvedConfig:
    return ResolvedConfig(
        profile=None,
        connection=ConnectionSettings(
            endpoint=endpoint,
            timeout=30.0,
            verify_ssl=True,
            cert_dir=None,
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


def test_flow_template_list_uses_derived_oneflow_endpoint(monkeypatch: Any) -> None:
    fake = FakeUrlOpen(
        [json.dumps({"DOCUMENT_POOL": {"DOCUMENT": [{"ID": "7", "NAME": "svc"}]}}).encode("utf-8")]
    )
    monkeypatch.setattr("opennebula_cli.services.flow_template.urlopen", fake)

    service = OneFlowTemplateService(_config())
    result = service.run_official("list", [])

    assert isinstance(result, list)
    assert result[0]["ID"] == "7"
    assert fake.calls[0]["method"] == "GET"
    assert fake.calls[0]["url"] == "http://frontend:2474/service_template"


def test_flow_template_instantiate_multiple_posts_actions(monkeypatch: Any, tmp_path: Path) -> None:
    merge_file = tmp_path / "merge.json"
    merge_file.write_text('{"name": "runtime-name"}', encoding="utf-8")

    fake = FakeUrlOpen(
        [
            json.dumps({"DOCUMENT": {"ID": "20"}}).encode("utf-8"),
            json.dumps({"DOCUMENT": {"ID": "21"}}).encode("utf-8"),
        ]
    )
    monkeypatch.setattr("opennebula_cli.services.flow_template.urlopen", fake)

    service = OneFlowTemplateService(_config())
    result = service.run_official(
        "instantiate",
        ["4", str(merge_file), "--multiple", "2"],
    )

    assert isinstance(result, list)
    assert [ack.id for ack in result] == [20, 21]
    assert all(isinstance(ack, Ack) for ack in result)
    for call in fake.calls:
        assert call["method"] == "POST"
        assert call["url"] == "http://frontend:2474/service_template/4/action"
        payload = json.loads((call["data"] or b"{}").decode("utf-8"))
        assert payload["action"]["perform"] == "instantiate"
        assert payload["action"]["params"]["merge_template"]["name"] == "runtime-name"


def test_flow_template_chgrp_sends_action_params(monkeypatch: Any) -> None:
    fake = FakeUrlOpen([b"{}"])
    monkeypatch.setattr("opennebula_cli.services.flow_template.urlopen", fake)

    service = OneFlowTemplateService(_config("http://flow.example:2474"))
    result = service.run_official("chgrp", ["8", "3"])

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Ack)
    assert result[0].id == 8
    assert fake.calls[0]["url"] == "http://flow.example:2474/service_template/8/action"
    payload = json.loads((fake.calls[0]["data"] or b"{}").decode("utf-8"))
    assert payload == {"action": {"perform": "chgrp", "params": {"group_id": 3}}}
