"""Typer application entrypoint."""


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
from opennebula_cli.cli.state import build_app_state
from opennebula_cli.lock_enforcer import ensure_command_allowed
from opennebula_cli.versioning import app_version, git_hash

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Modern OpenNebula CLI and SDK for OpenNebula 7.0.x.",
)

def _resource_lock_callback(resource_name: str):
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
def show_version() -> None:
    """Print app and git revision metadata."""

    typer.echo(f"opennebula-cli version: {app_version()}")
    typer.echo(f"opennebula-cli git hash: {git_hash()}")


@app.callback()
def root_callback(
    profile: str | None = typer.Option(None, "--profile", help="Profile name"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="OpenNebula XML-RPC endpoint"),
    auth: str | None = typer.Option(None, "--auth", help="Auth value or path"),
    user: str | None = typer.Option(None, "--user", help="Username"),
    password: str | None = typer.Option(None, "--password", prompt=False, hide_input=True),
    output: str = typer.Option("table", "--output", help="table|json|yaml|xml|csv|raw"),
    no_pager: bool = typer.Option(False, "--no-pager", help="Disable pager output"),
    timeout: float | None = typer.Option(None, "--timeout", help="Transport timeout in seconds"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Disable TLS verification"),
    cert_dir: str | None = typer.Option(None, "--cert-dir", help="Certificate directory"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
) -> None:
    """Build runtime state for subcommands."""

    ctx = click.get_current_context()
    if ctx.resilient_parsing:
        return
    ctx.obj = build_app_state(
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
