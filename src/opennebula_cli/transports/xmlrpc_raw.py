"""Fallback raw XML-RPC transport."""

from __future__ import annotations

import builtins
import ssl
import xmlrpc.client
from typing import Any

from opennebula_cli.sdk.exceptions import ApiError, ConnectionError, TimeoutError, TlsError


class RawXmlRpcTransport:
    """Minimal raw XML-RPC escape hatch for unsupported PyONE cases."""

    def __init__(
        self,
        endpoint: str,
        session: str,
        *,
        timeout: float,
        verify_ssl: bool,
        cert_dir: str | None = None,
    ) -> None:
        self._session = session
        if endpoint.startswith("https://"):
            context = ssl.create_default_context()
            if cert_dir:
                context.load_verify_locations(capath=cert_dir)
            if not verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            transport: xmlrpc.client.Transport = xmlrpc.client.SafeTransport(context=context)
        else:
            transport = xmlrpc.client.Transport()
        transport.timeout = timeout  # type: ignore[attr-defined]
        self._server = xmlrpc.client.ServerProxy(endpoint, transport=transport, allow_none=True)

    def call(self, method: str, *args: object) -> Any:
        """Invoke a raw XML-RPC method with the session argument prepended."""

        try:
            target: Any = self._server
            for part in method.split("."):
                if part == "one":
                    continue
                target = getattr(target, part)
            return target(self._session, *args)
        except ssl.SSLError as exc:
            raise TlsError(str(exc)) from exc
        except builtins.TimeoutError as exc:
            raise TimeoutError(str(exc)) from exc
        except OSError as exc:
            raise ConnectionError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - depends on live backend
            raise ApiError(str(exc)) from exc
