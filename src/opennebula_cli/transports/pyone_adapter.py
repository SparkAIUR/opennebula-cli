"""PyONE-backed transport adapter."""

from __future__ import annotations

import builtins
import inspect
import re
import ssl
import xmlrpc.client
from typing import Any

from opennebula_cli.sdk.exceptions import (
    ApiError,
    ApiFault,
    AuthError,
    ConnectionError,
    TimeoutError,
    TlsError,
)


class PyoneTransport:
    """Primary XML-RPC transport backed by PyONE."""

    def __init__(
        self,
        endpoint: str,
        session: str,
        *,
        timeout: float,
        verify_ssl: bool,
        cert_dir: str | None = None,
    ) -> None:
        try:
            import pyone
        except ImportError as exc:  # pragma: no cover - dependency error is environment-specific
            raise ConnectionError("pyone is not installed.") from exc

        kwargs: dict[str, object] = {"session": session, "timeout": timeout}
        parameters = inspect.signature(pyone.OneServer).parameters
        if "https_verify" in parameters:
            kwargs["https_verify"] = verify_ssl
        if cert_dir and "cert_dir" in parameters:
            kwargs["cert_dir"] = cert_dir
        self._client = pyone.OneServer(endpoint, **kwargs)

    @property
    def name(self) -> str:
        return "pyone"

    def supports(self, method: str) -> bool:
        """Check local binding availability without contacting OpenNebula."""

        try:
            target = self._resolve_method(method)
        except (AttributeError, TypeError):
            return False
        return callable(target)

    def call(self, method: str, *args: object) -> Any:
        """Resolve and invoke a dotted PyONE method."""

        try:
            target = self._resolve_method(method)
            return target(*args)
        except xmlrpc.client.Fault as exc:
            raise ApiFault(
                str(exc),
                fault_code=int(exc.faultCode),
                fault_string=str(exc.faultString),
                method=method,
                transport=self.name,
            ) from exc
        except ssl.SSLError as exc:
            raise TlsError(str(exc), method=method, transport=self.name) from exc
        except builtins.TimeoutError as exc:
            raise TimeoutError(str(exc), method=method, transport=self.name) from exc
        except OSError as exc:
            raise ConnectionError(str(exc), method=method, transport=self.name) from exc
        except Exception as exc:  # pragma: no cover - depends on live backend
            message = str(exc)
            lowered = message.lower()
            exception_name = type(exc).__name__
            known_fault_codes = {
                "OneAuthenticationException": 0x0100,
                "OneAuthorizationException": 0x0200,
                "OneNoExistsException": 0x0400,
                "OneActionException": 0x0800,
                "OneApiException": 0x1000,
                "OneInternalException": 0x2000,
            }
            parsed_fault = re.search(r"<Fault\s+(-?\d+):", message)
            fault_code = known_fault_codes.get(exception_name)
            if parsed_fault is not None:
                fault_code = int(parsed_fault.group(1))
            if fault_code is not None:
                raise ApiFault(
                    message,
                    fault_code=fault_code,
                    fault_string=message,
                    method=method,
                    transport=self.name,
                ) from exc
            if "auth" in lowered or "login" in lowered:
                raise AuthError(message, method=method, transport=self.name) from exc
            raise ApiError(message, method=method, transport=self.name) from exc

    def _resolve_method(self, method: str) -> Any:
        current: Any = self._client
        for part in method.split("."):
            if part == "one":
                continue
            current = getattr(current, part)
        return current
