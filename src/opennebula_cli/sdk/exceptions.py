"""Stable SDK exception hierarchy."""


class OpenNebulaError(Exception):
    """Base exception for the project."""


class AuthError(OpenNebulaError):
    """Raised when auth resolution or auth with the API fails."""


class ConnectionError(OpenNebulaError):
    """Raised when connection setup or connectivity fails."""


class TlsError(ConnectionError):
    """Raised when TLS verification fails."""


class TimeoutError(ConnectionError):
    """Raised when a transport call times out."""


class ApiError(OpenNebulaError):
    """Raised when the backend returns an application error."""


class PluginError(OpenNebulaError):
    """Raised when plugin loading or dispatch fails."""
