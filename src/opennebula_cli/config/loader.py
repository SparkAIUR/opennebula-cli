"""Runtime config resolution entrypoints."""

from __future__ import annotations

from pathlib import Path

from opennebula_cli.config.defaults import default_config_path
from opennebula_cli.config.merge import merge_runtime_config
from opennebula_cli.config.models import ProfileConfig, ResolvedConfig
from opennebula_cli.config.profiles import load_config_file
from opennebula_cli.sdk.exceptions import ConnectionError


def resolve_runtime_config(
    *,
    profile_name: str | None,
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
    config_path: Path | None = None,
) -> ResolvedConfig:
    """Resolve runtime config from all supported inputs."""

    config_file = load_config_file(config_path or default_config_path())
    selected = profile_name or config_file.default_profile
    profile: ProfileConfig | None = None
    if selected:
        profile = config_file.profiles.get(selected)
        if profile is None:
            raise ConnectionError(f"Profile '{selected}' was not found.")
    return merge_runtime_config(
        profile_name=selected,
        profile=profile,
        cli_endpoint=endpoint,
        cli_auth=auth,
        cli_user=user,
        cli_password=password,
        cli_output=output,
        cli_no_pager=no_pager,
        cli_timeout=timeout,
        cli_no_verify=no_verify,
        cli_cert_dir=cert_dir,
        verbose=verbose,
        debug=debug,
    )
