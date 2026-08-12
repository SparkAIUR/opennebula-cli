"""Stable SDK exception hierarchy and structured error metadata."""

from __future__ import annotations

from typing import Any


class OpenNebulaError(Exception):
    """Base exception for the project."""

    error_type = "opennebula_error"

    def __init__(
        self,
        message: str,
        *,
        method: str | None = None,
        context: str | None = None,
        endpoint: str | None = None,
        transport: str | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.method = method
        self.context = context
        self.endpoint = endpoint
        self.transport = transport
        self.hint = hint

    def error_detail(self) -> dict[str, Any]:
        """Return JSON-safe, non-secret error detail."""

        detail: dict[str, Any] = {
            "schema_version": "1",
            "type": self.error_type,
            "message": str(self),
        }
        for key in ("method", "context", "endpoint", "transport", "hint"):
            value = getattr(self, key, None)
            if value is not None:
                detail[key] = value
        return detail


class AuthError(OpenNebulaError):
    """Raised when auth resolution or auth with the API fails."""

    error_type = "authentication_error"


class ConnectionError(OpenNebulaError):
    """Raised when connection setup or connectivity fails."""

    error_type = "connection_error"


class TlsError(ConnectionError):
    """Raised when TLS verification fails."""

    error_type = "tls_error"


class TimeoutError(ConnectionError):
    """Raised when a transport call times out."""

    error_type = "timeout_error"


class ApiError(OpenNebulaError):
    """Raised when the backend returns an application error."""

    error_type = "api_error"


class PluginError(OpenNebulaError):
    """Raised when plugin loading or dispatch fails."""

    error_type = "plugin_error"


class ApiFault(ApiError):
    """Structured XML-RPC fault returned by OpenNebula."""

    error_type = "api_fault"

    def __init__(self, message: str, *, fault_code: int, fault_string: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.fault_code = fault_code
        self.fault_string = fault_string

    def error_detail(self) -> dict[str, Any]:
        detail = super().error_detail()
        detail["fault_code"] = self.fault_code
        detail["fault_string"] = self.fault_string
        return detail


class UnsupportedCapabilityError(OpenNebulaError):
    """Raised before an unsupported operation contacts its service."""

    error_type = "unsupported_capability"


class PolicyError(OpenNebulaError):
    """Raised when a context or local policy denies an operation."""

    error_type = "policy_denied"


class PartialFailureError(OpenNebulaError):
    """Raised when one or more batch/composite members fail."""

    error_type = "partial_failure"

    def __init__(self, message: str, *, failures: list[dict[str, Any]], **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.failures = failures

    def error_detail(self) -> dict[str, Any]:
        detail = super().error_detail()
        detail["failures"] = self.failures
        return detail
