"""Workflow template render/import service."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.sdk.models.common import Ack
from opennebula_cli.services.template import TemplateService

WORKFLOW_FILE = "workflow.yaml"
VM_TEMPLATE_FILE = "vm-template.one.j2"
CLOUD_INIT_FILE = "cloud-init.yaml.j2"
VARS_EXAMPLE_FILE = "vars.example.yaml"

STARTER_WORKFLOW = """version: 1
kind: workflow-template
template:
  source: vm-template.one.j2
cloud_init:
  source: cloud-init.yaml.j2
defaults:
  cpu: 1
  vcpu: 1
  memory_mb: 2048
  disk_size_mb: 10240
required:
  - template_name
  - image_name
  - network_name
"""

STARTER_TEMPLATE = """NAME = \"{{ template_name }}\"
CPU = \"{{ cpu }}\"
VCPU = \"{{ vcpu }}\"
MEMORY = \"{{ memory_mb }}\"

DISK = [ IMAGE = \"{{ image_name }}\", SIZE = \"{{ disk_size_mb }}\" ]
NIC = [ NETWORK = \"{{ network_name }}\" ]

CONTEXT = [
  NETWORK = \"YES\",
  SET_HOSTNAME = \"$NAME\",
  USER_DATA = \"{{ cloud_init_user_data_escaped }}\"{% for key, value in bootstrap_env_items %},
  {{ key }} = \"{{ value | replace('\\\\', '\\\\\\\\') | replace('\\"', '\\\\"') }}\"{% endfor %}
]
"""

STARTER_CLOUD_INIT = """#cloud-config
package_update: true
packages:
  - curl

write_files:
  - path: /etc/openclaw.env
    permissions: "0600"
    content: |
{% for key, value in bootstrap_env.items() %}
      {{ key }}={{ value }}
{% endfor %}

runcmd:
  - [ bash, -lc, "echo 'cloud-init bootstrap finished'" ]
"""

STARTER_VARS = """template_name: openclaw-ubuntu-template
cpu: 2
vcpu: 2
memory_mb: 4096
disk_size_mb: 20480
image_name: Ubuntu 24.04
network_name: Public
bootstrap_env:
  OPENCLAW_USER: alice
  OPENCLAW_TOKEN: replace-me
"""


class WorkflowTemplateSource(BaseModel):
    """OpenNebula template source descriptor."""

    model_config = ConfigDict(frozen=True)

    source: str


class WorkflowCloudInit(BaseModel):
    """Cloud-init source configuration."""

    model_config = ConfigDict(frozen=True)

    source: str | None = None
    inline: str | None = None

    @model_validator(mode="after")
    def _validate_source(self) -> WorkflowCloudInit:
        if self.source and self.inline:
            raise ValueError("cloud_init.source and cloud_init.inline are mutually exclusive")
        if not self.source and not self.inline:
            raise ValueError("cloud_init requires either source or inline")
        return self


class WorkflowTemplateSpec(BaseModel):
    """Workflow template specification."""

    model_config = ConfigDict(frozen=True)

    version: Literal[1]
    kind: Literal["workflow-template"]
    template: WorkflowTemplateSource
    cloud_init: WorkflowCloudInit | None = None
    defaults: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


@dataclass(slots=True, frozen=True)
class RenderedWorkflowTemplate:
    """Rendered OpenNebula template and merged variables."""

    template_text: str
    variables: dict[str, Any]
    template_name: str | None


class WorkflowTemplateService:
    """Render workflow specs into OpenNebula templates and import them."""

    def __init__(self, template_service: TemplateService | None = None) -> None:
        self._template_service = template_service

    def init(self, target_dir: Path, *, force: bool = False) -> list[Path]:
        """Create starter workflow files in the target directory."""

        target = target_dir.expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)

        files = {
            WORKFLOW_FILE: STARTER_WORKFLOW,
            VM_TEMPLATE_FILE: STARTER_TEMPLATE,
            CLOUD_INIT_FILE: STARTER_CLOUD_INIT,
            VARS_EXAMPLE_FILE: STARTER_VARS,
        }

        for relative_path in files:
            candidate = target / relative_path
            if candidate.exists() and not force:
                raise ApiError(f"Refusing to overwrite existing file: {candidate}")

        created: list[Path] = []
        for relative_path, content in files.items():
            destination = target / relative_path
            destination.write_text(content, encoding="utf-8")
            created.append(destination)

        return created

    def render_workflow(
        self,
        workflow_path: Path,
        *,
        vars_file: Path | None = None,
        cli_vars: list[str] | None = None,
        require_template_name: bool = False,
    ) -> RenderedWorkflowTemplate:
        """Render a workflow definition to OpenNebula template text."""

        spec_path = workflow_path.expanduser().resolve()
        spec = self._load_spec(spec_path)

        merged_vars = self._resolve_variables(
            spec,
            spec_path,
            vars_file=vars_file,
            cli_vars=cli_vars,
        )

        template_name_raw = merged_vars.get("template_name")
        template_name = None
        if template_name_raw is not None:
            template_name = str(template_name_raw).strip() or None
        if require_template_name and not template_name:
            raise ApiError("template_name is required for import/apply")

        template_source = self._resolve_relative_path(spec_path.parent, spec.template.source)
        rendered_template = self._render_template_file(
            template_source,
            merged_vars,
            workflow_dir=spec_path.parent,
        )

        return RenderedWorkflowTemplate(
            template_text=rendered_template,
            variables=merged_vars,
            template_name=template_name,
        )

    def import_workflow(
        self,
        workflow_path: Path,
        *,
        vars_file: Path | None = None,
        cli_vars: list[str] | None = None,
        rendered_output_file: Path | None = None,
    ) -> Ack:
        """Render and import a workflow-backed template into OpenNebula."""

        if self._template_service is None:
            raise ApiError("Template import requires an initialized TemplateService")

        rendered = self.render_workflow(
            workflow_path,
            vars_file=vars_file,
            cli_vars=cli_vars,
            require_template_name=True,
        )
        if rendered.template_name is None:
            raise ApiError("template_name is required for import/apply")

        self._ensure_template_name_available(rendered.template_name)

        output_path: Path | None = None
        if rendered_output_file is not None:
            output_path = rendered_output_file.expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered.template_text, encoding="utf-8")

        ack = self._template_service.create(rendered.template_text)
        message = f"Imported workflow template '{rendered.template_name}'."
        if output_path is not None:
            message = f"{message} Rendered template written to {output_path}."
        return ack.model_copy(update={"message": message})

    def _load_spec(self, workflow_path: Path) -> WorkflowTemplateSpec:
        try:
            raw = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ApiError(f"Unable to read workflow file {workflow_path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ApiError(f"Invalid workflow YAML in {workflow_path}: {exc}") from exc

        if not isinstance(raw, Mapping):
            raise ApiError(f"Workflow file must contain a mapping: {workflow_path}")

        try:
            return WorkflowTemplateSpec.model_validate(dict(raw))
        except ValidationError as exc:
            raise ApiError(f"Invalid workflow spec in {workflow_path}: {exc}") from exc

    def _resolve_variables(
        self,
        spec: WorkflowTemplateSpec,
        workflow_path: Path,
        *,
        vars_file: Path | None,
        cli_vars: list[str] | None,
    ) -> dict[str, Any]:
        merged: dict[str, Any] = dict(spec.defaults)

        if vars_file is not None:
            file_vars = self._load_vars_file(workflow_path.parent, vars_file)
            merged.update(file_vars)

        cli_overrides = self._parse_cli_vars(cli_vars or [])
        merged.update(cli_overrides)

        missing = [
            key
            for key in spec.required
            if key not in merged or merged[key] is None or str(merged[key]).strip() == ""
        ]
        if missing:
            missing_values = ", ".join(sorted(missing))
            raise ApiError(f"Missing required workflow variables: {missing_values}")

        bootstrap_env_raw = merged.get("bootstrap_env", {})
        if bootstrap_env_raw is None:
            bootstrap_env_raw = {}
        if not isinstance(bootstrap_env_raw, Mapping):
            raise ApiError("bootstrap_env must be a mapping")
        bootstrap_env = {str(key): str(value) for key, value in bootstrap_env_raw.items()}
        merged["bootstrap_env"] = bootstrap_env

        cloud_init_user_data = self._render_cloud_init(spec, workflow_path, merged)

        merged["cloud_init_user_data"] = cloud_init_user_data
        merged["cloud_init_user_data_escaped"] = self._escape_opennebula_string(
            cloud_init_user_data
        )
        merged["bootstrap_env_items"] = sorted(bootstrap_env.items())

        return merged

    @staticmethod
    def _parse_cli_vars(entries: list[str]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for entry in entries:
            if "=" not in entry:
                raise ApiError(f"Invalid --var value '{entry}', expected key=value")
            key, raw_value = entry.split("=", 1)
            key = key.strip()
            if not key:
                raise ApiError(f"Invalid --var value '{entry}', key cannot be empty")
            try:
                value = yaml.safe_load(raw_value)
            except yaml.YAMLError as exc:
                raise ApiError(f"Invalid value for --var {key}: {exc}") from exc
            parsed[key] = value
        return parsed

    def _load_vars_file(self, workflow_dir: Path, vars_file: Path) -> dict[str, Any]:
        target = self._resolve_relative_path(workflow_dir, str(vars_file))
        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            raise ApiError(f"Unable to read vars file {target}: {exc}") from exc

        try:
            if target.suffix.lower() == ".json":
                raw = json.loads(text)
            else:
                raw = yaml.safe_load(text)
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise ApiError(f"Invalid vars file {target}: {exc}") from exc

        if raw is None:
            return {}
        if not isinstance(raw, Mapping):
            raise ApiError(f"Vars file must contain a mapping: {target}")
        return dict(raw)

    def _render_cloud_init(
        self,
        spec: WorkflowTemplateSpec,
        workflow_path: Path,
        variables: dict[str, Any],
    ) -> str:
        if spec.cloud_init is None:
            return ""

        if spec.cloud_init.source is not None:
            source = self._resolve_relative_path(workflow_path.parent, spec.cloud_init.source)
            return self._render_template_file(source, variables, workflow_dir=workflow_path.parent)

        inline = spec.cloud_init.inline
        if inline is None:
            return ""

        return self._render_template_text(inline, variables, workflow_dir=workflow_path.parent)

    def _ensure_template_name_available(self, template_name: str) -> None:
        if self._template_service is None:
            raise ApiError("Template import requires an initialized TemplateService")

        for existing in self._template_service.list():
            if existing.name == template_name:
                raise ApiError(f"Template '{template_name}' already exists")

    @staticmethod
    def _resolve_relative_path(base_dir: Path, value: str) -> Path:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = (base_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.exists():
            raise ApiError(f"Referenced file does not exist: {candidate}")
        return candidate

    def _render_template_file(
        self,
        source: Path,
        variables: dict[str, Any],
        *,
        workflow_dir: Path,
    ) -> str:
        env = self._build_jinja_environment(
            loader=FileSystemLoader(str(source.parent)),
            workflow_dir=workflow_dir,
        )
        try:
            template = env.get_template(source.name)
            return template.render(**variables)
        except TemplateError as exc:
            raise ApiError(f"Failed to render template {source}: {exc}") from exc

    def _render_template_text(
        self,
        template_text: str,
        variables: dict[str, Any],
        *,
        workflow_dir: Path,
    ) -> str:
        env = self._build_jinja_environment(loader=None, workflow_dir=workflow_dir)
        try:
            template = env.from_string(template_text)
            return template.render(**variables)
        except TemplateError as exc:
            raise ApiError(f"Failed to render inline template: {exc}") from exc

    def _build_jinja_environment(
        self,
        *,
        loader: FileSystemLoader | None,
        workflow_dir: Path,
    ) -> Environment:
        env = Environment(
            loader=loader,
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        env.globals["read_file"] = lambda path: self._read_text_file(workflow_dir, path)
        env.globals["read_file_b64"] = lambda path: self._read_file_b64(workflow_dir, path)
        env.globals["fetch_url"] = self._fetch_url_text
        return env

    def _read_text_file(self, workflow_dir: Path, path: str) -> str:
        target = self._resolve_relative_path(workflow_dir, path)
        try:
            return target.read_text(encoding="utf-8")
        except OSError as exc:
            raise ApiError(f"Unable to read file {target}: {exc}") from exc

    def _read_file_b64(self, workflow_dir: Path, path: str) -> str:
        target = self._resolve_relative_path(workflow_dir, path)
        try:
            return base64.b64encode(target.read_bytes()).decode("ascii")
        except OSError as exc:
            raise ApiError(f"Unable to read file {target}: {exc}") from exc

    def _fetch_url_text(
        self,
        url: str,
        *,
        method: str | None = "GET",
        headers: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        timeout: float = 10.0,
        body: str | bytes | Mapping[str, Any] | None = None,
        encoding: str | None = None,
    ) -> str:
        target_url = self._build_fetch_url(url, params)
        request_method = self._normalize_http_method(method)
        request_headers = self._normalize_headers(headers)
        request_body = self._normalize_request_body(body, request_headers)
        request_timeout = self._normalize_timeout(timeout)
        request = Request(
            target_url,
            method=request_method,
            headers=request_headers,
            data=request_body,
        )

        try:
            with urlopen(request, timeout=request_timeout) as response:
                content = bytes(response.read())
                response_charset_raw = response.headers.get_content_charset()
                response_charset = (
                    str(response_charset_raw) if response_charset_raw is not None else None
                )
        except HTTPError as exc:
            reason = exc.reason or "HTTP error"
            raise ApiError(f"Unable to fetch URL {target_url}: HTTP {exc.code} {reason}") from exc
        except URLError as exc:
            reason = str(exc.reason) if exc.reason is not None else "request failed"
            raise ApiError(f"Unable to fetch URL {target_url}: {reason}") from exc
        except TimeoutError as exc:
            raise ApiError(f"Unable to fetch URL {target_url}: timed out") from exc
        except OSError as exc:
            raise ApiError(f"Unable to fetch URL {target_url}: {exc}") from exc

        text_encoding = encoding or response_charset or "utf-8"
        try:
            return content.decode(text_encoding)
        except LookupError as exc:
            raise ApiError(f"Invalid fetch_url encoding '{text_encoding}'") from exc
        except UnicodeDecodeError as exc:
            raise ApiError(
                f"Unable to decode URL content from {target_url} with encoding '{text_encoding}'"
            ) from exc

    @staticmethod
    def _build_fetch_url(url: str, params: Mapping[str, Any] | None) -> str:
        target_url = str(url).strip()
        if not target_url:
            raise ApiError("fetch_url requires a non-empty url")
        parsed = urlparse(target_url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ApiError(f"fetch_url only supports http/https URLs: {target_url}")

        if params is None:
            return target_url
        if not isinstance(params, Mapping):
            raise ApiError("fetch_url params must be a mapping")

        query_items = list(parse_qsl(parsed.query, keep_blank_values=True))
        for key, value in params.items():
            if isinstance(value, (list, tuple)):
                query_items.extend((str(key), str(item)) for item in value)
            else:
                query_items.append((str(key), str(value)))

        query = urlencode(query_items, doseq=True)
        return urlunparse(parsed._replace(query=query))

    @staticmethod
    def _normalize_http_method(method: str | None) -> str:
        normalized = str(method).strip().upper() if method is not None else ""
        if not normalized:
            normalized = "GET"
        allowed = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        if normalized not in allowed:
            raise ApiError(f"Unsupported fetch_url method '{normalized}'")
        return normalized

    @staticmethod
    def _normalize_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
        if headers is None:
            return {}
        if not isinstance(headers, Mapping):
            raise ApiError("fetch_url headers must be a mapping")
        return {str(key): str(value) for key, value in headers.items()}

    @staticmethod
    def _normalize_request_body(
        body: str | bytes | Mapping[str, Any] | None,
        headers: dict[str, str],
    ) -> bytes | None:
        if body is None:
            return None
        if isinstance(body, bytes):
            return body
        if isinstance(body, str):
            return body.encode("utf-8")
        if not isinstance(body, Mapping):
            raise ApiError("fetch_url body must be str, bytes, or a mapping")

        fields: list[tuple[str, str]] = []
        for key, value in body.items():
            if isinstance(value, (list, tuple)):
                fields.extend((str(key), str(item)) for item in value)
            else:
                fields.append((str(key), str(value)))
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        return urlencode(fields, doseq=True).encode("utf-8")

    @staticmethod
    def _normalize_timeout(timeout: float) -> float:
        try:
            value = float(timeout)
        except (TypeError, ValueError) as exc:
            raise ApiError("fetch_url timeout must be a positive number") from exc
        if value <= 0:
            raise ApiError("fetch_url timeout must be a positive number")
        return value

    @staticmethod
    def _escape_opennebula_string(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
