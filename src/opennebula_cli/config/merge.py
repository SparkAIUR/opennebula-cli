"""Merge config sources into runtime settings."""

from __future__ import annotations

import os
from typing import cast

from opennebula_cli.auth.context_config import load_auth_config
from opennebula_cli.auth.resolver import resolve_auth
from opennebula_cli.config.defaults import default_auth_path
from opennebula_cli.config.endpoints import SERVICE_PORTS, derive_service_endpoint
from opennebula_cli.config.models import (
    ALL_OUTPUT_MODES,
    ConnectionSettings,
    OutputMode,
    OutputSettings,
    ProfileConfig,
    ResolvedConfig,
)
from opennebula_cli.sdk.exceptions import ConnectionError
from opennebula_cli.state_store import StateStore


def _env_bool(name: str) -> bool | None:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _pick(*values: object) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None


def _resolve_contextual_credentials() -> tuple[
    str | None,
    str | None,
    str | None,
    dict[str, str],
    dict[str, str],
    str | None,
    str | None,
]:
    """Resolve endpoint and auth from auth.yaml or state DB contexts."""

    auth_config = load_auth_config()
    if auth_config is not None:
        current = auth_config.resolve_current()
        if current is not None:
            return (
                current.endpoint,
                f"literal:{current.auth.username}:{current.auth.password}",
                f"auth-config:{current.name}",
                dict(current.endpoints or {}),
                dict(current.config or {}),
                current.name,
                current.version,
            )

    context = StateStore().get_active_context()
    if context is not None:
        return (
            context.endpoint,
            f"literal:{context.username}:{context.password}",
            f"state-context:{context.name}",
            {},
            {},
            context.name,
            context.version,
        )
    return (None, None, None, {}, {}, None, None)


def _resolve_named_context(
    name: str | None,
) -> tuple[
    str | None, str | None, str | None, dict[str, str], dict[str, str], str | None, str | None
]:
    """Resolve a context for one invocation without changing active state."""

    if name is None:
        return _resolve_contextual_credentials()
    auth_config = load_auth_config()
    selected = auth_config.resolve_named(name) if auth_config else None
    if selected is not None:
        return (
            selected.endpoint,
            f"literal:{selected.auth.username}:{selected.auth.password}",
            f"auth-config:{selected.name}",
            dict(selected.endpoints or {}),
            dict(selected.config or {}),
            selected.name,
            selected.version,
        )
    stored = StateStore().get_context(name)
    if stored is not None:
        return (
            stored.endpoint,
            f"literal:{stored.username}:{stored.password}",
            f"state-context:{stored.name}",
            {},
            {},
            stored.name,
            stored.version,
        )
    raise ConnectionError(f"Context '{name}' was not found.")


def merge_runtime_config(
    *,
    profile_name: str | None,
    context_name: str | None = None,
    require_context: str | None = None,
    profile: ProfileConfig | None,
    cli_endpoint: str | None,
    cli_auth: str | None,
    cli_user: str | None,
    cli_password: str | None,
    cli_output: str,
    cli_no_pager: bool,
    cli_timeout: float | None,
    cli_no_verify: bool,
    cli_cert_dir: str | None,
    verbose: int,
    debug: bool,
) -> ResolvedConfig:
    """Merge CLI, profile, env, and defaults into a resolved config."""

    active_profile = profile or ProfileConfig()
    (
        context_endpoint,
        context_auth,
        context_source,
        context_service_endpoints,
        context_config,
        selected_context_name,
        context_version,
    ) = _resolve_named_context(context_name)
    if require_context is not None and selected_context_name != require_context:
        actual = selected_context_name or "<none>"
        raise ConnectionError(
            f"Required context '{require_context}' does not match selected context '{actual}'."
        )
    endpoint = _pick(
        cli_endpoint,
        active_profile.endpoint,
        context_endpoint,
        os.getenv("ONE_XMLRPC"),
    )
    if endpoint is None:
        raise ConnectionError(
            "No OpenNebula endpoint resolved. Use --endpoint, ONE_XMLRPC, or a profile."
        )

    timeout_value = _pick(
        cli_timeout,
        active_profile.timeout,
        os.getenv("ONE_XMLRPC_TIMEOUT"),
        60.0,
    )
    verify_ssl = (
        not cli_no_verify
        if cli_no_verify
        else _pick(
            active_profile.verify_ssl,
            not (_env_bool("ONE_DISABLE_SSL_VERIFY") or False),
            True,
        )
    )
    cert_dir = _pick(cli_cert_dir, active_profile.cert_dir, os.getenv("ONE_CERT_DIR"))
    output_value = cli_output or active_profile.output or "table"
    if output_value not in ALL_OUTPUT_MODES:
        output_value = "table"
    no_pager = cli_no_pager or bool(active_profile.no_pager)
    pool_page_size = os.getenv("ONE_POOL_PAGE_SIZE")
    output_settings = OutputSettings(
        output=cast(OutputMode, output_value),
        no_pager=no_pager,
        pager=os.getenv("ONE_PAGER"),
        listconf=os.getenv("ONE_LISTCONF"),
        pool_page_size=int(pool_page_size) if pool_page_size else None,
    )
    auth = resolve_auth(
        cli_auth=cli_auth,
        cli_user=cli_user,
        cli_password=cli_password,
        profile_auth=active_profile.auth,
        context_auth=context_auth,
        context_source=context_source,
        env_auth=os.getenv("ONE_AUTH"),
        default_auth_path=default_auth_path(),
    )
    if os.getenv("ONEFORM_URL"):
        context_service_endpoints["oneform"] = str(os.environ["ONEFORM_URL"])
    connection = ConnectionSettings(
        endpoint=str(endpoint),
        timeout=float(cast(float | str, timeout_value)),
        verify_ssl=bool(verify_ssl),
        cert_dir=str(cert_dir) if cert_dir else None,
        service_endpoints={
            service: (
                context_service_endpoints[service].rstrip("/")
                if service == "oneform"
                else derive_service_endpoint(
                    str(endpoint), service=service, explicit=context_service_endpoints.get(service)
                )
            )
            for service in SERVICE_PORTS
            if service != "oneform" or service in context_service_endpoints
        },
        service_config=context_config,
    )
    return ResolvedConfig(
        profile=profile_name,
        context_name=selected_context_name,
        context_version=context_version,
        mutation_policy=(
            "deny" if context_config.get("mutation_policy", "allow").lower() == "deny" else "allow"
        ),
        connection=connection,
        auth=auth,
        output=output_settings,
        verbose=verbose,
        debug=debug,
    )
