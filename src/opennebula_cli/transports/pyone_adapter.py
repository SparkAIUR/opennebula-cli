"""PyONE-backed transport adapter."""

from __future__ import annotations

import builtins
import inspect
import ssl
from typing import Any

from opennebula_cli.sdk.exceptions import (
    ApiError,
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

    def call(self, method: str, *args: object) -> Any:
        """Resolve and invoke a dotted PyONE method."""

        try:
            target = self._resolve_method(method)
            return target(*args)
        except ssl.SSLError as exc:
            raise TlsError(str(exc)) from exc
        except builtins.TimeoutError as exc:
            raise TimeoutError(str(exc)) from exc
        except OSError as exc:
            raise ConnectionError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - depends on live backend
            message = str(exc)
            lowered = message.lower()
            if "auth" in lowered or "login" in lowered:
                raise AuthError(message) from exc
            raise ApiError(message) from exc

    def _resolve_method(self, method: str) -> Any:
        current: Any = self._client
        for part in method.split("."):
            if part == "one":
                continue
            current = getattr(current, part)
        return current
