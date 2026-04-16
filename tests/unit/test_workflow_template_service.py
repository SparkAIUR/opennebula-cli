from __future__ import annotations

import base64
from collections.abc import Mapping
from email.message import Message
from pathlib import Path
from typing import Any, cast
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.services.template import TemplateService
from opennebula_cli.services.workflow_template import WorkflowTemplateService


class StubTransport:
    def __init__(self, responses: Mapping[str, object]) -> None:
        self._responses: dict[str, object] = dict(responses)
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


class StubHttpResponse:
    def __init__(self, payload: bytes, *, charset: str | None = "utf-8") -> None:
        self._payload = payload
        self.headers = Message()
        if charset is not None:
            self.headers.add_header("Content-Type", f"text/plain; charset={charset}")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> StubHttpResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


@pytest.fixture
def workflow_dir(tmp_path: Path) -> Path:
    root = tmp_path / "workflow"
    root.mkdir()
    (root / "workflow.yaml").write_text(
        """version: 1
kind: workflow-template
template:
  source: vm-template.one.j2
cloud_init:
  source: cloud-init.yaml.j2
defaults:
  cpu: 1
  greeting: hello
  bootstrap_env:
    DEFAULT_KEY: default
required:
  - template_name
  - image_name
""",
        encoding="utf-8",
    )
    (root / "vm-template.one.j2").write_text(
        """NAME = "{{ template_name }}"
CPU = "{{ cpu }}"
DISK = [ IMAGE = "{{ image_name }}" ]
CONTEXT = [
  USER_DATA = "{{ cloud_init_user_data_escaped }}"{% for key, value in bootstrap_env_items %},
  {{ key }} = "{{ value }}"{% endfor %}
]
""",
        encoding="utf-8",
    )
    (root / "cloud-init.yaml.j2").write_text(
        """#cloud-config
runcmd:
  - echo {{ greeting }}
""",
        encoding="utf-8",
    )
    return root


def test_init_writes_starter_files(tmp_path: Path) -> None:
    service = WorkflowTemplateService()

    created = service.init(tmp_path / "starter")

    created_names = sorted(path.name for path in created)
    assert created_names == [
        "cloud-init.yaml.j2",
        "vars.example.yaml",
        "vm-template.one.j2",
        "workflow.yaml",
    ]


def test_render_workflow_merges_vars_with_precedence(workflow_dir: Path) -> None:
    service = WorkflowTemplateService()
    vars_file = workflow_dir / "vars.yaml"
    vars_file.write_text(
        """cpu: 2
image_name: ubuntu-cloud
bootstrap_env:
  FILE_KEY: file
""",
        encoding="utf-8",
    )

    rendered = service.render_workflow(
        workflow_dir / "workflow.yaml",
        vars_file=vars_file,
        cli_vars=["cpu=3", "template_name=openclaw-template"],
    )

    assert rendered.template_name == "openclaw-template"
    assert 'CPU = "3"' in rendered.template_text
    assert 'NAME = "openclaw-template"' in rendered.template_text
    assert 'DISK = [ IMAGE = "ubuntu-cloud" ]' in rendered.template_text
    assert 'USER_DATA = "#cloud-config\\nruncmd:\\n  - echo hello\\n"' in rendered.template_text
    assert 'FILE_KEY = "file"' in rendered.template_text
    assert 'DEFAULT_KEY = "default"' not in rendered.template_text


def test_render_workflow_cloud_init_can_read_file_content(workflow_dir: Path) -> None:
    (workflow_dir / "files").mkdir()
    (workflow_dir / "files" / "openclaw.env").write_text(
        "OPENCLAW_MODE=production\nOPENCLAW_REGION=us-central\n",
        encoding="utf-8",
    )
    (workflow_dir / "cloud-init.yaml.j2").write_text(
        """#cloud-config
write_files:
  - path: /etc/openclaw.env
    permissions: "0600"
    content: |
{{ read_file("files/openclaw.env") | indent(6, true) }}
""",
        encoding="utf-8",
    )

    service = WorkflowTemplateService()
    rendered = service.render_workflow(
        workflow_dir / "workflow.yaml",
        cli_vars=["template_name=openclaw-template", "image_name=ubuntu-cloud"],
    )

    assert "OPENCLAW_MODE=production" in rendered.template_text
    assert "OPENCLAW_REGION=us-central" in rendered.template_text


def test_render_workflow_cloud_init_can_read_file_content_as_base64(workflow_dir: Path) -> None:
    payload = b"\x00\x01openclaw"
    (workflow_dir / "files").mkdir()
    (workflow_dir / "files" / "payload.bin").write_bytes(payload)
    (workflow_dir / "cloud-init.yaml.j2").write_text(
        """#cloud-config
write_files:
  - path: /opt/payload.bin
    encoding: b64
    content: {{ read_file_b64("files/payload.bin") }}
""",
        encoding="utf-8",
    )

    service = WorkflowTemplateService()
    rendered = service.render_workflow(
        workflow_dir / "workflow.yaml",
        cli_vars=["template_name=openclaw-template", "image_name=ubuntu-cloud"],
    )

    expected = base64.b64encode(payload).decode("ascii")
    assert expected in rendered.template_text


def test_render_workflow_cloud_init_read_file_fails_for_missing_file(workflow_dir: Path) -> None:
    (workflow_dir / "cloud-init.yaml.j2").write_text(
        """#cloud-config
write_files:
  - path: /etc/openclaw.env
    content: |
{{ read_file("files/missing.env") | indent(6, true) }}
""",
        encoding="utf-8",
    )

    service = WorkflowTemplateService()

    with pytest.raises(ApiError, match="Referenced file does not exist"):
        service.render_workflow(
            workflow_dir / "workflow.yaml",
            cli_vars=["template_name=openclaw-template", "image_name=ubuntu-cloud"],
        )


def test_render_workflow_cloud_init_can_fetch_url_content(
    workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: float) -> StubHttpResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return StubHttpResponse(b"#!/usr/bin/env bash\necho fetched-script\n")

    monkeypatch.setattr("opennebula_cli.services.workflow_template.urlopen", fake_urlopen)
    (workflow_dir / "cloud-init.yaml.j2").write_text(
        """#cloud-config
write_files:
  - path: /opt/remote-bootstrap.sh
    permissions: "0755"
    content: |
{{ fetch_url(
  "https://example.com/bootstrap.sh",
  method="POST",
  headers={"Authorization": "Bearer test-token", "X-Trace-Id": "trace-123"},
  params={"ref": "main", "component": ["core", "cli"]},
  timeout=5,
  body={"mode": "prod", "version": 7}
) | indent(6, true) }}
""",
        encoding="utf-8",
    )

    service = WorkflowTemplateService()
    rendered = service.render_workflow(
        workflow_dir / "workflow.yaml",
        cli_vars=["template_name=openclaw-template", "image_name=ubuntu-cloud"],
    )

    assert "echo fetched-script" in rendered.template_text
    assert captured["timeout"] == 5
    request = cast(Any, captured["request"])
    assert hasattr(request, "get_method")
    assert hasattr(request, "full_url")
    assert hasattr(request, "header_items")
    assert hasattr(request, "data")

    method = request.get_method()
    url = request.full_url
    headers = {key.lower(): value for key, value in request.header_items()}
    payload = request.data

    assert method == "POST"
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert query["ref"] == ["main"]
    assert sorted(query["component"]) == ["cli", "core"]
    assert headers["authorization"] == "Bearer test-token"
    assert headers["x-trace-id"] == "trace-123"
    assert headers["content-type"] == "application/x-www-form-urlencoded"
    assert payload == b"mode=prod&version=7"


def test_render_workflow_cloud_init_fetch_url_fails_gracefully(
    workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_urlopen(_: object, timeout: float) -> StubHttpResponse:
        raise URLError("host unreachable")

    monkeypatch.setattr("opennebula_cli.services.workflow_template.urlopen", fake_urlopen)
    (workflow_dir / "cloud-init.yaml.j2").write_text(
        """#cloud-config
write_files:
  - path: /etc/openclaw.env
    content: |
{{ fetch_url("https://example.com/bootstrap.env") | indent(6, true) }}
""",
        encoding="utf-8",
    )

    service = WorkflowTemplateService()
    with pytest.raises(ApiError, match="Unable to fetch URL https://example.com/bootstrap.env"):
        service.render_workflow(
            workflow_dir / "workflow.yaml",
            cli_vars=["template_name=openclaw-template", "image_name=ubuntu-cloud"],
        )


def test_render_workflow_requires_declared_variables(workflow_dir: Path) -> None:
    service = WorkflowTemplateService()

    with pytest.raises(ApiError, match="Missing required workflow variables"):
        service.render_workflow(workflow_dir / "workflow.yaml")


def test_render_workflow_rejects_conflicting_cloud_init(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """version: 1
kind: workflow-template
template:
  source: vm-template.one.j2
cloud_init:
  source: cloud-init.yaml.j2
  inline: |
    #cloud-config
required:
  - template_name
""",
        encoding="utf-8",
    )
    (tmp_path / "vm-template.one.j2").write_text('NAME = "{{ template_name }}"\n', encoding="utf-8")
    (tmp_path / "cloud-init.yaml.j2").write_text("#cloud-config\n", encoding="utf-8")

    service = WorkflowTemplateService()
    with pytest.raises(ApiError, match="cloud_init.source and cloud_init.inline"):
        service.render_workflow(workflow, cli_vars=["template_name=test"])


def test_import_workflow_fails_when_template_name_exists(workflow_dir: Path) -> None:
    transport = StubTransport(
        {
            "one.templatepool.info": {
                "VMTEMPLATE": [
                    {
                        "ID": 7,
                        "NAME": "openclaw-template",
                        "REGTIME": 1,
                        "TEMPLATE": {},
                    }
                ]
            },
            "one.template.allocate": 42,
        }
    )
    service = WorkflowTemplateService(template_service=TemplateService(transport))

    with pytest.raises(ApiError, match="already exists"):
        service.import_workflow(
            workflow_dir / "workflow.yaml",
            cli_vars=["template_name=openclaw-template", "image_name=ubuntu-cloud"],
        )

    assert transport.calls == [("one.templatepool.info", (-2, -1, -1))]


def test_import_workflow_allocates_template_and_can_write_rendered_output(
    workflow_dir: Path,
) -> None:
    transport = StubTransport(
        {"one.templatepool.info": {"VMTEMPLATE": []}, "one.template.allocate": 42}
    )
    service = WorkflowTemplateService(template_service=TemplateService(transport))
    output_file = workflow_dir / "rendered.one"

    result = service.import_workflow(
        workflow_dir / "workflow.yaml",
        cli_vars=["template_name=openclaw-template", "image_name=ubuntu-cloud"],
        rendered_output_file=output_file,
    )

    assert result.resource == "template"
    assert result.action == "create"
    assert result.id == 42
    assert result.message is not None
    assert "openclaw-template" in result.message
    assert output_file.exists()
    assert 'NAME = "openclaw-template"' in output_file.read_text(encoding="utf-8")
    assert len(transport.calls) == 2
    assert transport.calls[0] == ("one.templatepool.info", (-2, -1, -1))
    assert transport.calls[1][0] == "one.template.allocate"
