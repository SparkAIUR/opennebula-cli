"""OneFlow service template parity service.

This service is a REST fallback for oneflow-template commands that are outside
OpenNebula's XML-RPC surface and not covered by PyONE.
"""

from __future__ import annotations

import json
import ssl
import sys
from base64 import b64encode
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from opennebula_cli.config.models import ResolvedConfig
from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.sdk.models.common import Ack, ensure_list, normalize_value
from opennebula_cli.services.official import parse_id_list, parse_official_args, require_positionals


class OneFlowTemplateService:
    """Official oneflow-template command support over OneFlow REST."""

    def __init__(self, config: ResolvedConfig) -> None:
        self._config = config

    def run_official(self, verb: str, argv: list[str]) -> object:
        """Run a oneflow-template command with loose official argv parsing."""

        parsed = parse_official_args(argv)

        if verb in {"list", "top"}:
            return self._list(parsed)
        if verb == "show":
            return self._show(parsed)
        if verb == "create":
            return self._create(parsed)
        if verb == "update":
            return self._update(parsed)
        if verb == "delete":
            return self._delete(parsed)
        if verb == "rename":
            return self._rename(parsed)
        if verb == "clone":
            return self._clone(parsed)
        if verb == "instantiate":
            return self._instantiate(parsed)
        if verb in {"chgrp", "chown", "chmod"}:
            return self._admin_action(verb, parsed)

        raise ApiError(f"Unsupported flow-template command: {verb}")

    def _list(self, parsed: Any) -> object:
        payload = self._request_json("GET", "/service_template", parsed)
        documents = ensure_list(self._nested_get(payload, "DOCUMENT_POOL", "DOCUMENT"))
        return [normalize_value(document) for document in documents]

    def _show(self, parsed: Any) -> object:
        template_id = int(require_positionals(parsed, 1, "show <templateid>")[0])
        payload = self._request_json("GET", f"/service_template/{template_id}", parsed)
        return normalize_value(self._nested_get(payload, "DOCUMENT", default=payload))

    def _create(self, parsed: Any) -> object:
        body = self._json_input(parsed, positional_index=0, usage="create [file]")
        payload = self._request_json("POST", "/service_template", parsed, json_body=body)
        template_id = self._extract_id(payload)
        return Ack(resource="flow-template", id=template_id, action="create")

    def _update(self, parsed: Any) -> object:
        positionals = require_positionals(parsed, 1, "update <templateid> [file]")
        template_id = int(positionals[0])
        body = self._json_input(parsed, positional_index=1, usage="update <templateid> [file]")
        payload = self._request_json(
            "PUT",
            f"/service_template/{template_id}",
            parsed,
            json_body=body,
        )
        result_id = self._extract_id(payload, fallback=template_id)
        return Ack(resource="flow-template", id=result_id, action="update")

    def _delete(self, parsed: Any) -> object:
        ids = parse_id_list(require_positionals(parsed, 1, "delete <range|templateid_list>")[0])
        query: dict[str, str] = {}
        if "delete_images" in parsed.flags:
            query["delete_images"] = "true"
        if "delete_templates" in parsed.flags or "delete_vm_templates" in parsed.flags:
            query["delete_templates"] = "true"

        results: list[Ack] = []
        for template_id in ids:
            self._request_json("DELETE", f"/service_template/{template_id}", parsed, query=query)
            results.append(Ack(resource="flow-template", id=template_id, action="delete"))
        return results

    def _rename(self, parsed: Any) -> object:
        positionals = require_positionals(parsed, 2, "rename <templateid> <name>")
        template_id = int(positionals[0])
        name = positionals[1]

        current = self._request_json("GET", f"/service_template/{template_id}", parsed)
        body = self._template_body(current)
        body["name"] = name
        payload = self._request_json(
            "PUT",
            f"/service_template/{template_id}",
            parsed,
            json_body=body,
        )
        result_id = self._extract_id(payload, fallback=template_id)
        return Ack(resource="flow-template", id=result_id, action="rename")

    def _clone(self, parsed: Any) -> object:
        positionals = require_positionals(parsed, 2, "clone <templateid> <name>")
        source_id = int(positionals[0])
        new_name = positionals[1]

        current = self._request_json("GET", f"/service_template/{source_id}", parsed)
        body = self._template_body(current)
        body["name"] = new_name
        payload = self._request_json("POST", "/service_template", parsed, json_body=body)
        clone_id = self._extract_id(payload)
        message = None
        if "recursive" in parsed.flags or "recursive_templates" in parsed.flags:
            message = "recursive clone flags were accepted; backend applies available behavior"
        return Ack(resource="flow-template", id=clone_id, action="clone", message=message)

    def _instantiate(self, parsed: Any) -> object:
        positionals = require_positionals(parsed, 1, "instantiate <templateid> [file]")
        template_id = int(positionals[0])
        merge_template = self._maybe_json_input(parsed, positional_index=1)

        multiple_raw = parsed.options.get("multiple", "1")
        try:
            multiple = max(1, int(multiple_raw))
        except ValueError as exc:
            raise ApiError(f"Invalid --multiple value: {multiple_raw}") from exc

        params: dict[str, object] = {}
        if merge_template is not None:
            params["merge_template"] = merge_template

        action_body: dict[str, object] = {"action": {"perform": "instantiate"}}
        if params:
            action_body["action"] = {"perform": "instantiate", "params": params}

        results: list[Ack] = []
        for _ in range(multiple):
            payload = self._request_json(
                "POST",
                f"/service_template/{template_id}/action",
                parsed,
                json_body=action_body,
            )
            service_id = self._extract_id(payload, fallback=template_id)
            results.append(Ack(resource="service", id=service_id, action="instantiate"))

        return results[0] if len(results) == 1 else results

    def _admin_action(self, verb: str, parsed: Any) -> object:
        positionals = require_positionals(parsed, 2, f"{verb} <range|templateid_list> <value>")
        ids = parse_id_list(positionals[0])

        results: list[Ack] = []
        for template_id in ids:
            params: dict[str, object]
            if verb == "chgrp":
                params = {"group_id": int(positionals[1])}
            elif verb == "chown":
                group_id = int(positionals[2]) if len(positionals) > 2 else -1
                params = {"user_id": int(positionals[1]), "group_id": group_id}
            else:
                params = {"octet": positionals[1]}

            action_body = {"action": {"perform": verb, "params": params}}
            self._request_json(
                "POST",
                f"/service_template/{template_id}/action",
                parsed,
                json_body=action_body,
            )
            results.append(Ack(resource="flow-template", id=template_id, action=verb))
        return results

    def _request_json(
        self,
        method: str,
        path: str,
        parsed: Any,
        *,
        json_body: Mapping[str, object] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> object:
        base_url = self._server_url(parsed)
        target_url = self._build_url(base_url, path, query)
        payload = json.dumps(json_body).encode("utf-8") if json_body is not None else None

        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {self._basic_auth_token()}",
        }
        oneflow_host = self._config.connection.service_config.get("oneflow_host")
        if oneflow_host:
            headers["Host"] = oneflow_host
        if payload is not None:
            headers["Content-Type"] = "application/json"

        request = Request(target_url, method=method, headers=headers, data=payload)

        try:
            with urlopen(
                request,
                timeout=self._config.connection.timeout,
                context=self._ssl_context(),
            ) as response:
                data = bytes(response.read())
        except HTTPError as exc:
            detail = self._decode_http_error(exc)
            raise ApiError(f"OneFlow request failed ({method} {target_url}): {detail}") from exc
        except URLError as exc:
            reason = str(exc.reason) if exc.reason is not None else "request failed"
            raise ApiError(f"OneFlow request failed ({method} {target_url}): {reason}") from exc
        except TimeoutError as exc:
            raise ApiError(f"OneFlow request failed ({method} {target_url}): timed out") from exc
        except OSError as exc:
            raise ApiError(f"OneFlow request failed ({method} {target_url}): {exc}") from exc

        if not data:
            return {}
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(f"OneFlow returned non-JSON payload for {method} {target_url}") from exc

    def _server_url(self, parsed: Any) -> str:
        explicit = parsed.options.get("server") or parsed.options.get("s")
        if explicit:
            return str(explicit).rstrip("/")
        derived = self._config.connection.service_endpoints.get("oneflow")
        if derived:
            return derived.rstrip("/")
        endpoint = self._config.connection.endpoint
        parsed_endpoint = urlparse(endpoint)
        if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.hostname:
            raise ApiError(f"Unable to derive OneFlow endpoint from ONE_XMLRPC: {endpoint}")

        hostname = parsed_endpoint.hostname
        port = parsed_endpoint.port
        if port in {None, 2474}:
            netloc = parsed_endpoint.netloc
        else:
            netloc = f"{hostname}:2474"

        return f"{parsed_endpoint.scheme}://{netloc}".rstrip("/")

    def _build_url(
        self,
        base_url: str,
        path: str,
        query: Mapping[str, str] | None,
    ) -> str:
        parsed = urlparse(f"{base_url.rstrip('/')}/{path.lstrip('/')}")
        items = list(parse_qsl(parsed.query, keep_blank_values=True))
        if query:
            items.extend((str(key), str(value)) for key, value in query.items())
        final: ParseResult = parsed._replace(query=urlencode(items, doseq=True))
        return urlunparse(final)

    def _basic_auth_token(self) -> str:
        raw = f"{self._config.auth.username}:{self._config.auth.secret}".encode()
        return b64encode(raw).decode("ascii")

    def _ssl_context(self) -> ssl.SSLContext | None:
        if not self._config.connection.endpoint.startswith("https://"):
            return None
        context = ssl.create_default_context()
        if self._config.connection.cert_dir:
            context.load_verify_locations(capath=self._config.connection.cert_dir)
        if not self._config.connection.verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def _json_input(self, parsed: Any, *, positional_index: int, usage: str) -> dict[str, object]:
        body = self._maybe_json_input(parsed, positional_index=positional_index)
        if body is None:
            raise ApiError(f"Missing JSON template input. Usage: {usage}")
        return body

    def _maybe_json_input(self, parsed: Any, *, positional_index: int) -> dict[str, object] | None:
        file_value = parsed.options.get("file") or parsed.options.get("f")
        candidate = None
        if file_value:
            candidate = str(file_value)
        elif len(parsed.positionals) > positional_index:
            candidate = parsed.positionals[positional_index]

        if candidate:
            try:
                text = open(candidate, encoding="utf-8").read()
            except OSError as exc:
                raise ApiError(f"Unable to read file {candidate}: {exc}") from exc
            return self._parse_json(text, source=candidate)

        if not sys.stdin.isatty():
            text = sys.stdin.read()
            if text.strip():
                return self._parse_json(text, source="stdin")

        return None

    def _parse_json(self, text: str, *, source: str) -> dict[str, object]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ApiError(f"Invalid JSON in {source}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ApiError(f"Expected a JSON object in {source}")
        return payload

    @staticmethod
    def _nested_get(payload: object, *keys: str, default: object | None = None) -> object:
        current = payload
        for key in keys:
            if not isinstance(current, Mapping):
                return default
            current = current.get(key)
        return current

    def _template_body(self, payload: object) -> dict[str, object]:
        body = self._nested_get(payload, "DOCUMENT", "TEMPLATE", "BODY")
        if not isinstance(body, Mapping):
            raise ApiError("OneFlow response does not include DOCUMENT.TEMPLATE.BODY")
        return dict(body)

    def _extract_id(self, payload: object, *, fallback: int | None = None) -> int:
        for candidate in (
            self._nested_get(payload, "DOCUMENT", "ID"),
            self._nested_get(payload, "ID"),
            self._nested_get(payload, "document", "id"),
        ):
            if candidate is None:
                continue
            try:
                return int(str(candidate))
            except ValueError:
                continue
        if fallback is not None:
            return fallback
        raise ApiError("Unable to determine resource ID from OneFlow response")

    @staticmethod
    def _decode_http_error(exc: HTTPError) -> str:
        detail = f"HTTP {exc.code}"
        try:
            raw = exc.read().decode("utf-8")
        except Exception:  # pragma: no cover - defensive fallback
            return detail
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip() or detail
        message = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
        if isinstance(message, str) and message.strip():
            return f"HTTP {exc.code} {message.strip()}"
        return raw.strip() or detail
