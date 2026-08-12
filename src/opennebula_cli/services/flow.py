"""OneFlow service parity service."""

from __future__ import annotations

import json
import ssl
from base64 import b64encode
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import ParseResult, parse_qsl, quote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from opennebula_cli.config.models import ResolvedConfig
from opennebula_cli.sdk.exceptions import ApiError, PolicyError
from opennebula_cli.sdk.models.common import Ack, ensure_list
from opennebula_cli.sdk.models.flow import OneFlowServiceDocument
from opennebula_cli.services.official import (
    ParsedArgs,
    parse_id_list,
    parse_official_args,
    require_positionals,
)


class OneFlowService:
    """Official oneflow command support over OneFlow REST."""

    def __init__(self, config: ResolvedConfig) -> None:
        self._config = config

    def run_official(self, verb: str, argv: list[str]) -> object:
        parsed = parse_official_args(argv)
        if verb in {"list", "top"}:
            payload = self._request_json("GET", "/service", parsed)
            documents = ensure_list(self._nested_get(payload, "DOCUMENT_POOL", "DOCUMENT"))
            return [OneFlowServiceDocument.from_raw(document) for document in documents]
        if verb in {"show", "service"}:
            service_id = int(require_positionals(parsed, 1, "show <serviceid>")[0])
            payload = self._request_json("GET", f"/service/{service_id}", parsed)
            document = self._nested_get(payload, "DOCUMENT", default=payload)
            return OneFlowServiceDocument.from_raw(document)
        if self._config.mutation_policy == "deny":
            context = self._config.context_name or "<none>"
            raise PolicyError(f"Context '{context}' denies mutating OneFlow operations.")
        if verb == "delete":
            ids = parse_id_list(require_positionals(parsed, 1, "delete <range|serviceid_list>")[0])
            results: list[Ack] = []
            for service_id in ids:
                self._request_json("DELETE", f"/service/{service_id}", parsed)
                results.append(Ack(resource="flow", id=service_id, action=verb))
            return results
        if verb == "purge-done":
            self._request_json("POST", "/service_pool/purge_done", parsed, json_body={})
            return {"resource": "flow", "action": verb, "ok": True}
        if verb == "sched-delete":
            positionals = require_positionals(
                parsed, 3, "sched-delete <serviceid> <role_name> <sched_id>"
            )
            service_id = int(positionals[0])
            role = quote(positionals[1], safe="")
            schedule_id = int(positionals[2])
            self._request_json(
                "DELETE",
                f"/service/{service_id}/role/{role}/sched_action/{schedule_id}",
                parsed,
            )
            return Ack(resource="flow", id=service_id, action=verb)
        if verb in {
            "recover",
            "release",
            "chgrp",
            "chmod",
            "chown",
            "action",
            "scale",
            "rename",
            "update",
            "add-role",
            "remove-role",
        }:
            return self._service_action_or_update(verb, parsed)
        raise ApiError(f"Unsupported flow command: {verb}")

    def _service_action_or_update(self, verb: str, parsed: ParsedArgs) -> object:
        positionals = require_positionals(parsed, 1, f"{verb} <serviceid>")
        service_id = int(positionals[0])

        if verb == "rename":
            require_positionals(parsed, 2, "rename <serviceid> <name>")
            current = self._request_json("GET", f"/service/{service_id}", parsed)
            body = self._template_body(current)
            body["name"] = positionals[1]
            self._request_json("PUT", f"/service/{service_id}", parsed, json_body=body)
            return Ack(resource="flow", id=service_id, action=verb)

        if verb == "update":
            current = self._request_json("GET", f"/service/{service_id}", parsed)
            body = self._template_body(current)
            self._request_json("PUT", f"/service/{service_id}", parsed, json_body=body)
            return Ack(resource="flow", id=service_id, action=verb)

        if verb in {"add-role", "remove-role"}:
            perform = "add_role" if verb == "add-role" else "remove_role"
            role_action_body = {"action": {"perform": perform, "params": {}}}
            self._request_json(
                "POST",
                f"/service/{service_id}/role_action",
                parsed,
                json_body=role_action_body,
            )
            return Ack(resource="flow", id=service_id, action=verb)

        perform = verb
        params: dict[str, object] = {}
        if verb == "chgrp":
            require_positionals(parsed, 2, "chgrp <serviceid> <groupid>")
            params = {"group_id": int(positionals[1])}
        elif verb == "chown":
            require_positionals(parsed, 2, "chown <serviceid> <userid> [groupid]")
            group_id = int(positionals[2]) if len(positionals) > 2 else -1
            params = {"user_id": int(positionals[1]), "group_id": group_id}
        elif verb == "chmod":
            require_positionals(parsed, 2, "chmod <serviceid> <octet>")
            params = {"octet": positionals[1]}
        elif verb == "scale":
            require_positionals(parsed, 3, "scale <serviceid> <role> <cardinality>")
            params = {"role": positionals[1], "cardinality": int(positionals[2])}
        elif verb == "action" and len(positionals) > 1:
            perform = positionals[1]

        action_body: dict[str, object] = {"action": {"perform": perform}}
        if params:
            action_body["action"] = {"perform": perform, "params": params}
        self._request_json(
            "POST",
            f"/service/{service_id}/action",
            parsed,
            json_body=action_body,
        )
        return Ack(resource="flow", id=service_id, action=verb)

    def _request_json(
        self,
        method: str,
        path: str,
        parsed: object,
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
            reason = str(exc.reason) if exc.reason is not None else f"HTTP {exc.code}"
            raise ApiError(f"OneFlow request failed ({method} {target_url}): {reason}") from exc
        except URLError as exc:
            reason = str(exc.reason) if exc.reason is not None else "request failed"
            raise ApiError(f"OneFlow request failed ({method} {target_url}): {reason}") from exc

        if not data:
            return {}
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(f"OneFlow returned non-JSON payload for {method} {target_url}") from exc

    def _server_url(self, parsed: object) -> str:
        options = getattr(parsed, "options", {})
        explicit = options.get("server") or options.get("s")
        if explicit:
            return str(explicit).rstrip("/")
        derived = self._config.connection.service_endpoints.get("oneflow")
        if derived:
            return derived.rstrip("/")
        endpoint = self._config.connection.endpoint
        parsed_endpoint = urlparse(endpoint)
        if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.hostname:
            raise ApiError(f"Unable to derive OneFlow endpoint from ONE_XMLRPC: {endpoint}")
        return f"{parsed_endpoint.scheme}://{parsed_endpoint.hostname}:2474".rstrip("/")

    def _build_url(self, base_url: str, path: str, query: Mapping[str, str] | None) -> str:
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
