"""Endpoint derivation helpers for service-specific OpenNebula ports."""

from __future__ import annotations

from urllib.parse import urlparse

from opennebula_cli.sdk.exceptions import ConnectionError

SERVICE_PORTS: dict[str, int] = {
    "web": 9869,
    "firestone": 2616,
    "oneflow": 2474,
    # OneForm is intentionally explicit-only. Its port and proxy path are deployment-defined.
    "oneform": 13013,
}


def derive_service_endpoint(
    base_endpoint: str,
    *,
    service: str,
    explicit: str | None = None,
) -> str:
    """Return endpoint for a named service using override or default port substitution."""

    if explicit:
        return explicit.rstrip("/")

    port = SERVICE_PORTS.get(service)
    if port is None:
        raise ConnectionError(f"Unknown service endpoint mapping requested: {service}")

    parsed = urlparse(base_endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConnectionError(f"Unable to derive endpoint from ONE_XMLRPC: {base_endpoint}")

    return f"{parsed.scheme}://{parsed.hostname}:{port}"
