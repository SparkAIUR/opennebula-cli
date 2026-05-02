"""Typer application entrypoint."""

import sys

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

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Modern OpenNebula CLI and SDK for OpenNebula 7.0.x.",
)

app.add_typer(vm.app, name="vm")
app.add_typer(host.app, name="host")
app.add_typer(image.app, name="image")
app.add_typer(template.app, name="template")
app.add_typer(vnet.app, name="vnet")
app.add_typer(datastore.app, name="datastore")
app.add_typer(cluster.app, name="cluster")
app.add_typer(user.app, name="user")
app.add_typer(group.app, name="group")
app.add_typer(acl.app, name="acl")
app.add_typer(flow.app, name="flow")
app.add_typer(gate.app, name="gate")
app.add_typer(flow_template.app, name="flow-template")
app.add_typer(marketapp.app, name="marketapp")
app.add_typer(db.app, name="db")
app.add_typer(vdc.app, name="vdc")
app.add_typer(vrouter.app, name="vrouter")
app.add_typer(vmgroup.app, name="vmgroup")
app.add_typer(vntemplate.app, name="vntemplate")
app.add_typer(zone.app, name="zone")
app.add_typer(hook.app, name="hook")
app.add_typer(market.app, name="market")
app.add_typer(secgroup.app, name="secgroup")
app.add_typer(cfg.app, name="cfg")
app.add_typer(log.app, name="log")
app.add_typer(swap.app, name="swap")
app.add_typer(showback.app, name="showback")
app.add_typer(acct.app, name="acct")
app.add_typer(gather.app, name="gather")
app.add_typer(state.app, name="state")
app.add_typer(workflow.app, name="workflow")
app.add_typer(raw.app, name="raw")


@app.command("agents")
def agents() -> None:
    """Print the AI-agent guide."""

    typer.echo(AGENTS_GUIDE)


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
    try:
        invocation_args = list(sys.argv[1:])
        if not invocation_args and ctx.invoked_subcommand:
            invocation_args = [str(ctx.invoked_subcommand), *list(ctx.args)]
        ensure_command_allowed(invocation_args)
    except Exception as exc:
        raise_cli_error(exc)
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
