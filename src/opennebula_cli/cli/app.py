"""Typer application entrypoint."""

from collections.abc import Callable

import click
import typer

from opennebula_cli.cli.agents_guide import AGENTS_GUIDE
from opennebula_cli.cli.error_handlers import raise_cli_error
from opennebula_cli.cli.resources import (
    acct,
    acl,
    cfg,
    cluster,
    datastore,
    db,
    flow,
    flow_template,
    gate,
    gather,
    group,
    hook,
    host,
    image,
    log,
    market,
    marketapp,
    oneform,
    raw,
    secgroup,
    showback,
    state,
    swap,
    template,
    user,
    vdc,
    vm,
    vmgroup,
    vnet,
    vntemplate,
    vrouter,
    workflow,
    zone,
)
from opennebula_cli.cli.state import AppState, build_app_state
from opennebula_cli.config.models import CANONICAL_OUTPUT_MODE_HELP
from opennebula_cli.lock_enforcer import ensure_command_allowed
from opennebula_cli.versioning import app_version, git_hash

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Modern OpenNebula CLI and SDK for OpenNebula 7.0.x and 7.4.x.",
)


def _resource_lock_callback(resource_name: str) -> Callable[[typer.Context], None]:
    def _callback(ctx: typer.Context) -> None:
        click_ctx = click.get_current_context()
        if click_ctx.resilient_parsing:
            return
        invocation_args = [resource_name]
        if click_ctx.invoked_subcommand:
            invocation_args.append(str(click_ctx.invoked_subcommand))
        try:
            ensure_command_allowed(invocation_args)
        except Exception as exc:
            raise_cli_error(exc)

    return _callback


def _add_resource_typer(resource_name: str, resource_app: typer.Typer) -> None:
    app.add_typer(
        resource_app,
        name=resource_name,
        callback=_resource_lock_callback(resource_name),
    )


_add_resource_typer("vm", vm.app)
_add_resource_typer("host", host.app)
_add_resource_typer("image", image.app)
_add_resource_typer("template", template.app)
_add_resource_typer("vnet", vnet.app)
_add_resource_typer("datastore", datastore.app)
_add_resource_typer("cluster", cluster.app)
_add_resource_typer("user", user.app)
_add_resource_typer("group", group.app)
_add_resource_typer("acl", acl.app)
_add_resource_typer("flow", flow.app)
_add_resource_typer("gate", gate.app)
_add_resource_typer("flow-template", flow_template.app)
_add_resource_typer("marketapp", marketapp.app)
_add_resource_typer("form", oneform.form_app)
_add_resource_typer("provider", oneform.provider_app)
_add_resource_typer("provider-template", oneform.provider_template_app)
_add_resource_typer("provision", oneform.provision_app)
_add_resource_typer("provision-template", oneform.provision_template_app)
_add_resource_typer("db", db.app)
_add_resource_typer("vdc", vdc.app)
_add_resource_typer("vrouter", vrouter.app)
_add_resource_typer("vmgroup", vmgroup.app)
_add_resource_typer("vntemplate", vntemplate.app)
_add_resource_typer("zone", zone.app)
_add_resource_typer("hook", hook.app)
_add_resource_typer("market", market.app)
_add_resource_typer("secgroup", secgroup.app)
_add_resource_typer("cfg", cfg.app)
_add_resource_typer("log", log.app)
_add_resource_typer("swap", swap.app)
_add_resource_typer("showback", showback.app)
_add_resource_typer("acct", acct.app)
_add_resource_typer("gather", gather.app)
_add_resource_typer("state", state.app)
_add_resource_typer("workflow", workflow.app)
_add_resource_typer("raw", raw.app)


@app.command("agents")
def agents() -> None:
    """Print the AI-agent guide."""

    typer.echo(AGENTS_GUIDE)


@app.command("version")
def show_version(ctx: typer.Context) -> None:
    """Print app and git revision metadata."""

    state = ctx.find_object(AppState)
    if state is None:
        raise RuntimeError("CLI runtime state is not initialized.")
    if state.output in {"table", "human"}:
        typer.echo(f"opennebula-cli version: {app_version()}")
        typer.echo(f"opennebula-cli git hash: {git_hash()}")
        return
    state.render({"version": app_version(), "git_hash": git_hash()}, resource="opennebula-cli")


@app.command("capabilities")
def show_capabilities(ctx: typer.Context) -> None:
    """Authenticate and show the effective server capability profile."""

    state = ctx.find_object(AppState)
    if state is None:
        raise RuntimeError("CLI runtime state is not initialized.")
    try:
        client = state.client()
        state.render(
            {
                "server": client.server_info(),
                "capabilities": sorted(client.capabilities().methods),
            },
            resource="capability",
        )
    except Exception as exc:
        raise_cli_error(exc)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    """Check authenticated XML-RPC identity and configured service endpoints."""

    state = ctx.find_object(AppState)
    if state is None:
        raise RuntimeError("CLI runtime state is not initialized.")
    try:
        client = state.client()
        config = state.resolve_config()
        info = client.server_info()
        state.render(
            {
                "healthy": True,
                "context": config.context_name,
                "xmlrpc": {
                    "authenticated": True,
                    "endpoint": info.endpoint,
                    "server_version": info.version,
                    "profile": info.profile,
                    "transport": info.transport,
                },
                "services": {
                    name: {"configured": True, "endpoint": endpoint}
                    for name, endpoint in sorted(config.connection.service_endpoints.items())
                },
                "config_sources": {
                    "auth": config.auth.source,
                    "profile": config.profile,
                    "context": config.context_name,
                    "mutation_policy": config.mutation_policy,
                },
            },
            resource="doctor",
        )
    except Exception as exc:
        raise_cli_error(exc)


@app.callback()
def root_callback(
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
    context_name: str | None = typer.Option(
        None, "--context", help="Select a stored context for this command."
    ),
    require_context: str | None = typer.Option(
        None, "--require-context", help="Fail locally unless this exact context is selected."
    ),
    backend: str = typer.Option("auto", "--backend", help="Transport backend: auto|pyone|raw"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="OpenNebula XML-RPC endpoint"),
    auth: str | None = typer.Option(None, "--auth", help="Auth value or path"),
    user: str | None = typer.Option(None, "--user", help="Username"),
    password: str | None = typer.Option(None, "--password", prompt=False, hide_input=True),
    password_stdin: bool = typer.Option(
        False, "--password-stdin", help="Read the password from stdin."
    ),
    output: str = typer.Option("table", "--output", help=CANONICAL_OUTPUT_MODE_HELP),
    no_pager: bool = typer.Option(False, "--no-pager", help="Disable pager output"),
    timeout: float | None = typer.Option(None, "--timeout", help="Transport timeout in seconds"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Disable TLS verification"),
    cert_dir: str | None = typer.Option(None, "--cert-dir", help="Certificate directory"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
    compact: bool = typer.Option(False, "--compact", help="Emit compact JSON."),
    value_path: str | None = typer.Option(None, "--value", help="Emit one field path."),
    select_fields: str | None = typer.Option(None, "--select", help="Comma-separated field paths."),
    filter_expression: str | None = typer.Option(
        None, "--filter", help="Filter list items with path=value."
    ),
    sort_field: str | None = typer.Option(None, "--sort", help="Sort list items by a field path."),
    no_header: bool = typer.Option(False, "--no-header", help="Omit table headers."),
    full: bool = typer.Option(
        False, "--full", help="Use lossless normalized inspection where supported."
    ),
    official_schema: bool = typer.Option(
        False, "--official-schema", help="Use upstream field names and nesting where supported."
    ),
) -> None:
    """Build runtime state for subcommands."""

    ctx = click.get_current_context()
    if ctx.resilient_parsing:
        return
    if password_stdin:
        import sys

        password = sys.stdin.readline().rstrip("\r\n")
    ctx.obj = build_app_state(
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
