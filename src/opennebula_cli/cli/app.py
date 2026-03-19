"""Typer application entrypoint."""

import click
import typer

from opennebula_cli.cli.resources import host, image, template, vm
from opennebula_cli.cli.state import build_app_state

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Modern OpenNebula CLI and SDK for OpenNebula 7.0.x.",
)

app.add_typer(vm.app, name="vm")
app.add_typer(host.app, name="host")
app.add_typer(image.app, name="image")
app.add_typer(template.app, name="template")


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
