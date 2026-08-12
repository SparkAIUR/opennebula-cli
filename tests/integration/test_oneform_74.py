from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from opennebula_cli.auth.models import ResolvedAuth
from opennebula_cli.config.models import ConnectionSettings, ResolvedConfig
from opennebula_cli.sdk.exceptions import ConnectionError, UnsupportedCapabilityError
from opennebula_cli.services.oneform import (
    OneFormService,
    PreviewTemplateService,
    ProviderService,
    ProvisionService,
)
from opennebula_cli.transports.rest import JsonRestTransport


class OneFormHandler(BaseHTTPRequestHandler):
    calls: list[tuple[str, str, bool]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def _record(self) -> None:
        self.calls.append((self.command, self.path, bool(self.headers.get("Authorization"))))

    def _json(self, value: object) -> None:
        payload = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        self._record()
        if self.path == "/api/v1/redirect":
            self.send_response(302)
            self.send_header("Location", "https://example.invalid/credential-sink")
            self.end_headers()
            return
        if self.path.startswith("/api/v1/drivers/"):
            self._json({"name": "driver/name", "enabled": True})
            return
        self._json([{"name": "metal", "enabled": True}])

    def do_PATCH(self) -> None:
        self._record()
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length)) if length else {}
        self._json({"ID": 4, **body})


@pytest.fixture
def oneform_server() -> str:
    OneFormHandler.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), OneFormHandler)
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
        context_name="local-oneform",
        connection=ConnectionSettings(
            endpoint="http://127.0.0.1:2633/RPC2",
            service_endpoints={"oneform": endpoint},
        ),
        auth=ResolvedAuth(
            username="oneadmin",
            secret="test-only",
            source="test",
            raw_session="oneadmin:test-only",
        ),
    )


def test_oneform_routes_are_versioned_encoded_and_authenticated(oneform_server: str) -> None:
    service = OneFormService(config(oneform_server))
    provider = ProviderService(config(oneform_server))

    assert service.list()[0].name == "metal"
    assert service.show("driver/name").name == "driver/name"
    assert provider.update(4, {"name": "renamed"}).name == "renamed"
    assert OneFormHandler.calls == [
        ("GET", "/api/v1/drivers?enabled=false", True),
        ("GET", "/api/v1/drivers/driver%2Fname", True),
        ("PATCH", "/api/v1/providers/4", True),
    ]


def test_oneform_redirect_is_rejected_without_following(oneform_server: str) -> None:
    transport = JsonRestTransport(
        base_url=f"{oneform_server}/api/v1",
        username="oneadmin",
        password="test-only",
        timeout=2,
        verify_ssl=True,
        cert_dir=None,
    )

    with pytest.raises(ConnectionError, match="redirects are disabled"):
        transport.request("GET", "redirect")

    assert OneFormHandler.calls == [("GET", "/api/v1/redirect", True)]


def test_template_wrappers_are_disabled_by_default_without_contact(
    oneform_server: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENNEBULA_CLI_ENABLE_ONEFORM_PREVIEW", raising=False)
    service = PreviewTemplateService(config(oneform_server), "provider-template")

    with pytest.raises(UnsupportedCapabilityError, match="guarded preview"):
        service.list()

    assert OneFormHandler.calls == []


def test_oneform_provision_normalizes_official_document_body(oneform_server: str) -> None:
    document = {
        "DOCUMENT": {
            "ID": "19",
            "NAME": "document-name",
            "TEMPLATE": {
                "PROVISION_BODY": {
                    "name": "provision-name",
                    "state": "RUNNING",
                }
            },
        }
    }
    model = ProvisionService(config(oneform_server))._document(document)

    assert model.id == 19
    assert model.name == "provision-name"
    assert (model.state, model.state_id) == ("RUNNING", 6)
    assert model.raw == document


def test_oneform_unknown_numeric_state_remains_visible(oneform_server: str) -> None:
    model = ProvisionService(config(oneform_server))._document(
        {"DOCUMENT": {"ID": 20, "TEMPLATE": {"PROVISION_BODY": {"state": 99}}}}
    )

    assert (model.state, model.state_id) == ("UNKNOWN_99", 99)
