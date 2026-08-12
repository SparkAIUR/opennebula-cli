"""CLI runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console

from opennebula_cli.config.loader import resolve_runtime_config
from opennebula_cli.config.models import ResolvedConfig
from opennebula_cli.renderers import render_output
from opennebula_cli.renderers.base import RenderContext
from opennebula_cli.sdk.client import OneClient


@dataclass(slots=True)
class AppState:
    """Lazily resolved CLI application state."""

    profile: str | None
    context_name: str | None
    require_context: str | None
    backend: str
    endpoint: str | None
    auth: str | None
    user: str | None
    password: str | None
    output: str
    no_pager: bool
    timeout: float | None
    no_verify: bool
    cert_dir: str | None
    verbose: int
    debug: bool
    compact: bool = False
    value_path: str | None = None
    select_fields: str | None = None
    filter_expression: str | None = None
    sort_field: str | None = None
    no_header: bool = False
    full: bool = False
    official_schema: bool = False
    _config: ResolvedConfig | None = field(default=None, init=False, repr=False)
    _client: OneClient | None = field(default=None, init=False, repr=False)

    def resolve_config(self) -> ResolvedConfig:
        """Resolve runtime config on demand."""

        if self._config is None:
            self._config = resolve_runtime_config(
                profile_name=self.profile,
                context_name=self.context_name,
                require_context=self.require_context,
                endpoint=self.endpoint,
                auth=self.auth,
                user=self.user,
                password=self.password,
                output=self.output,
                no_pager=self.no_pager,
                timeout=self.timeout,
                no_verify=self.no_verify,
                cert_dir=self.cert_dir,
                verbose=self.verbose,
                debug=self.debug,
            )
        return self._config

    def client(self) -> OneClient:
        """Construct the SDK client lazily."""

        if self._client is None:
            self._client = OneClient.from_config(self.resolve_config(), backend=self.backend)
            self._client.server_info()
        return self._client

    def render(
        self,
        data: object,
        *,
        resource: str | None = None,
        output_override: str | None = None,
    ) -> None:
        """Render command output with the configured renderer."""

        selected_output = (output_override or self.output).lower()
        output = "table" if selected_output == "human" else selected_output
        interactive = output == "table"
        console = Console(
            force_terminal=interactive,
            color_system="auto" if interactive else None,
            stderr=False,
        )
        from opennebula_cli.renderers.selection import transform_output

        transformed = transform_output(
            data,
            value_path=self.value_path,
            select_fields=self.select_fields,
            filter_expression=self.filter_expression,
            sort_field=self.sort_field,
        )
        render_output(
            transformed,
            ctx=RenderContext(
                console=console,
                output=output,
                interactive=interactive,
                no_pager=self.no_pager,
                resource=resource,
                compact=self.compact,
                no_header=self.no_header,
                official_schema=self.official_schema,
            ),
        )

    def enforce_operation(self, resource: str, verb: str | None) -> None:
        """Apply context mutation policy before a server operation is attempted."""

        if verb is None or resource in {"state", "workflow", "raw"}:
            return
        read_only = {
            "list",
            "show",
            "top",
            "monitoring",
            "disk-list",
            "wait",
            "version",
            "get",
            "status",
            "validate",
            "diff",
            "logs",
        }
        if verb in read_only:
            return
        config = self.resolve_config()
        if config.mutation_policy == "deny":
            from opennebula_cli.sdk.exceptions import PolicyError

            raise PolicyError(
                f"Context '{config.context_name or '<none>'}' denies mutating operations."
            )


def build_app_state(
    *,
    profile: str | None,
    context_name: str | None,
    require_context: str | None,
    backend: str,
    endpoint: str | None,
    auth: str | None,
    user: str | None,
    password: str | None,
    output: str,
    no_pager: bool,
    timeout: float | None,
    no_verify: bool,
    cert_dir: str | None,
    verbose: int,
    debug: bool,
    compact: bool = False,
    value_path: str | None = None,
    select_fields: str | None = None,
    filter_expression: str | None = None,
    sort_field: str | None = None,
    no_header: bool = False,
    full: bool = False,
    official_schema: bool = False,
) -> AppState:
    """Create an AppState."""

    return AppState(
        profile=profile,
        context_name=context_name,
        require_context=require_context,
        backend=backend,
        endpoint=endpoint,
        auth=auth,
        user=user,
        password=password,
        output=output,
        no_pager=no_pager,
        timeout=timeout,
        no_verify=no_verify,
        cert_dir=cert_dir,
        verbose=verbose,
        debug=debug,
        compact=compact,
        value_path=value_path,
        select_fields=select_fields,
        filter_expression=filter_expression,
        sort_field=sort_field,
        no_header=no_header,
        full=full,
        official_schema=official_schema,
    )
