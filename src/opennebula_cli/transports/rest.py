"""Hardened JSON REST transport for OneFlow and OneForm APIs."""

from __future__ import annotations

import json
import ssl
from base64 import b64encode
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from opennebula_cli.sdk.exceptions import ApiError, AuthError, ConnectionError

MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        return None


class JsonRestTransport:
    """JSON client that never forwards credentials across redirects."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout: float,
        verify_ssl: bool,
        cert_dir: str | None,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ConnectionError(f"Invalid REST endpoint: {self._safe_url(base_url)}")
        self.base_url = base_url.rstrip("/") + "/"
        self._timeout = timeout
        self._authorization = "Basic " + b64encode(f"{username}:{password}".encode()).decode()
        context: ssl.SSLContext | None = None
        if parsed.scheme == "https":
            context = ssl.create_default_context()
            if cert_dir:
                context.load_verify_locations(capath=cert_dir)
            if not verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
        self._opener = build_opener(_RejectRedirects(), HTTPSHandler(context=context))

    @staticmethod
    def _safe_url(url: str) -> str:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
    ) -> object:
        target = urljoin(self.base_url, path.lstrip("/"))
        if query:
            target = f"{target}?{urlencode(query, doseq=True)}"
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "Accept": "application/json",
            "Authorization": self._authorization,
            "User-Agent": "opennebula-cli/7.4",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = Request(target, method=method, headers=headers, data=payload)
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_RESPONSE_BYTES:
                    raise ApiError("REST response exceeds the 16 MiB safety limit")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                raise ConnectionError(
                    f"REST redirects are disabled for authenticated requests: "
                    f"{self._safe_url(target)}"
                ) from exc
            if exc.code in {401, 403}:
                raise AuthError(f"REST authentication failed at {self._safe_url(target)}") from exc
            detail = self._error_detail(exc)
            raise ApiError(
                f"REST request failed with HTTP {exc.code}: {detail}",
                endpoint=self._safe_url(target),
            ) from exc
        except URLError as exc:
            raise ConnectionError(
                f"REST connection failed at {self._safe_url(target)}: {exc.reason}"
            ) from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ApiError("REST response exceeds the 16 MiB safety limit")
        if not raw:
            return {}
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(
                f"REST endpoint returned invalid JSON: {self._safe_url(target)}"
            ) from exc
        if isinstance(decoded, list):
            return [
                item.get("DOCUMENT", item) if isinstance(item, dict) else item for item in decoded
            ]
        if isinstance(decoded, dict) and "DOCUMENT" in decoded:
            return decoded["DOCUMENT"]
        return decoded

    @staticmethod
    def _error_detail(exc: HTTPError) -> str:
        try:
            raw = exc.read(64 * 1024)
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return str(exc.reason or "request failed")
        if isinstance(payload, dict):
            return str(payload.get("message") or payload.get("error") or exc.reason)
        return str(exc.reason or "request failed")
