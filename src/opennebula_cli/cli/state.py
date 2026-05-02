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
    _config: ResolvedConfig | None = field(default=None, init=False, repr=False)
    _client: OneClient | None = field(default=None, init=False, repr=False)

    def resolve_config(self) -> ResolvedConfig:
        """Resolve runtime config on demand."""

        if self._config is None:
            self._config = resolve_runtime_config(
                profile_name=self.profile,
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
            self._client = OneClient.from_config(self.resolve_config())
        return self._client

    def render(
        self,
        data: object,
        *,
        resource: str | None = None,
        output_override: str | None = None,
    ) -> None:
        """Render command output with the configured renderer."""

        config = self.resolve_config()
        selected_output = (output_override or config.output.output).lower()
        output = "table" if selected_output == "human" else selected_output
        interactive = output == "table"
        console = Console(
            force_terminal=interactive,
            color_system="auto" if interactive else None,
            stderr=False,
        )
        render_output(
            data,
            ctx=RenderContext(
                console=console,
                output=output,
                interactive=interactive,
                no_pager=config.output.no_pager,
                resource=resource,
            ),
        )


def build_app_state(
    *,
    profile: str | None,
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
) -> AppState:
    """Create an AppState."""

    return AppState(
        profile=profile,
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
    )
