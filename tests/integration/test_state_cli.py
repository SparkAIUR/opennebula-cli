from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from opennebula_cli.cli.app import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "OPENNEBULA_CLI_STATE_DB": str(tmp_path / "state.db"),
        "OPENNEBULA_CLI_AUTH_CONFIG": str(tmp_path / "missing-auth.yaml"),
    }


def test_state_ctx_set_and_use(tmp_path: Path) -> None:
    env = _env(tmp_path)
    result = runner.invoke(
        app,
        [
            "state",
            "ctx",
            "set",
            "--name",
            "staging",
            "--endpoint",
            "https://staging.example.com/RPC2",
            "--user",
            "user1",
            "--password",
            "pass1",
            "--version",
            "v7.0.2",
        ],
        env=env,
    )
    assert result.exit_code == 0
    assert "Context 'staging' set successfully" in result.stdout

    result_prod = runner.invoke(
        app,
        [
            "state",
            "ctx",
            "set",
            "--name",
            "production",
            "--endpoint",
            "https://prod.example.com/RPC2",
            "--user",
            "user2",
            "--password",
            "pass2",
            "--version",
            "v7.0.2",
        ],
        env=env,
    )
    assert result_prod.exit_code == 0

    use_result = runner.invoke(app, ["state", "ctx", "use", "staging"], env=env)
    assert use_result.exit_code == 0
    assert "Context switched to 'staging'" in use_result.stdout

    auth_config = Path(env["OPENNEBULA_CLI_AUTH_CONFIG"])
    payload = yaml.safe_load(auth_config.read_text(encoding="utf-8"))
    assert payload["current_context"] == "staging"

    get_result = runner.invoke(app, ["state", "ctx", "get"], env=env)
    assert get_result.exit_code == 0
    assert "name: staging (active)" in get_result.stdout
    assert "endpoint: https://staging.example.com/RPC2" in get_result.stdout

    show_result = runner.invoke(app, ["state", "ctx", "show", "staging"], env=env)
    assert show_result.exit_code == 0
    assert "name: staging (active)" in show_result.stdout

    list_result = runner.invoke(app, ["state", "ctx", "list"], env=env)
    assert list_result.exit_code == 0
    assert "- staging (active): endpoint=https://staging.example.com/RPC2" in list_result.stdout

    list_auth_result = runner.invoke(app, ["state", "ctx", "list", "--source", "auth"], env=env)
    assert list_auth_result.exit_code == 0
    assert "- production: endpoint=https://prod.example.com/RPC2" in list_auth_result.stdout

    list_db_result = runner.invoke(app, ["state", "ctx", "list", "--source", "db"], env=env)
    assert list_db_result.exit_code == 0
    assert "No contexts found." in list_db_result.stdout

    list_invalid = runner.invoke(app, ["state", "ctx", "list", "--source", "nope"], env=env)
    assert list_invalid.exit_code != 0
    assert "must be one of: auto, auth, db" in list_invalid.output


def test_state_lock_enable_blocks_command_then_disable(tmp_path: Path) -> None:
    env = _env(tmp_path)
    enable = runner.invoke(
        app,
        [
            "state",
            "lock",
            "enable",
            "--actions",
            "all",
            "--commands",
            "vm",
            "--password",
            "secret",
        ],
        input="secret\n",
        env=env,
    )
    assert enable.exit_code == 0
    assert "Commands locked successfully" in enable.stdout

    blocked = runner.invoke(app, ["vm", "list"], env=env)
    assert blocked.exit_code != 0
    assert "Command is locked by local state policy" in blocked.output

    disable = runner.invoke(
        app,
        ["state", "lock", "disable"],
        input="y\nsecret\n",
        env=env,
    )
    assert disable.exit_code == 0
    assert "Lock disabled successfully" in disable.stdout


def test_state_lock_enable_delete_without_commands_blocks_delete_across_commands(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    enable = runner.invoke(
        app,
        [
            "state",
            "lock",
            "enable",
            "--actions",
            "delete",
            "--commands",
            "",
        ],
        input="\n",
        env=env,
    )
    assert enable.exit_code == 0
    assert "Commands locked successfully" in enable.stdout

    blocked_template = runner.invoke(app, ["template", "delete", "42"], env=env)
    assert blocked_template.exit_code != 0
    assert "Command is locked by local state policy" in blocked_template.output

    blocked_image = runner.invoke(app, ["image", "delete", "42"], env=env)
    assert blocked_image.exit_code != 0
    assert "Command is locked by local state policy" in blocked_image.output

    allowed_show = runner.invoke(app, ["vm", "show", "42"], env=env)
    assert "Command is locked by local state policy" not in allowed_show.output

    disable = runner.invoke(app, ["state", "lock", "disable"], input="y\n", env=env)
    assert disable.exit_code == 0
    assert "Lock disabled successfully" in disable.stdout


def test_state_ctx_use_missing_context_errors(tmp_path: Path) -> None:
    result = runner.invoke(app, ["state", "ctx", "use", "missing"], env=_env(tmp_path))
    assert result.exit_code != 0
    assert "was not found in auth config" in result.output


def test_state_ctx_get_and_list_without_contexts(tmp_path: Path) -> None:
    env = _env(tmp_path)

    get_result = runner.invoke(app, ["state", "ctx", "get"], env=env)
    assert get_result.exit_code == 0
    assert "No active context is set." in get_result.stdout

    list_result = runner.invoke(app, ["state", "ctx", "list"], env=env)
    assert list_result.exit_code == 0
    assert "No contexts found." in list_result.stdout


def test_state_ctx_show_missing_context_errors(tmp_path: Path) -> None:
    env = _env(tmp_path)
    result = runner.invoke(app, ["state", "ctx", "show", "missing"], env=env)
    assert result.exit_code != 0
    assert "was not found in auth config" in result.output


def test_state_ctx_validate_checks_endpoints_and_prints_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env = _env(tmp_path)
    setup = runner.invoke(
        app,
        [
            "state",
            "ctx",
            "set",
            "--name",
            "staging",
            "--endpoint",
            "http://on.sprkinfra.com:2633/RPC2",
            "--user",
            "user1",
            "--password",
            "pass1",
        ],
        env=env,
    )
    assert setup.exit_code == 0

    monkeypatch.setattr(
        "opennebula_cli.cli.resources.state._check_endpoint",
        lambda _url, *, timeout: (True, f"timeout={timeout}"),
    )

    result = runner.invoke(app, ["state", "ctx", "validate", "--timeout", "3"], env=env)

    assert result.exit_code == 0
    assert "Context: staging" in result.stdout
    assert "checking xmlrpc" in result.stdout
    assert "checking oneflow" in result.stdout
    assert "checking firestone" in result.stdout
    assert "checking web" in result.stdout
    assert "Validation complete: 4/4 checks passed" in result.stdout


def test_state_ctx_validate_all_contexts(tmp_path: Path, monkeypatch) -> None:
    env = _env(tmp_path)
    for name in ("staging", "prod"):
        result = runner.invoke(
            app,
            [
                "state",
                "ctx",
                "set",
                "--name",
                name,
                "--endpoint",
                f"https://{name}.example.com/RPC2",
                "--user",
                name,
                "--password",
                "pass",
            ],
            env=env,
        )
        assert result.exit_code == 0

    monkeypatch.setattr(
        "opennebula_cli.cli.resources.state._check_endpoint",
        lambda _url, *, timeout: (True, f"timeout={timeout}"),
    )

    result = runner.invoke(app, ["state", "ctx", "validate", "--all"], env=env)
    assert result.exit_code == 0
    assert "Context: staging" in result.stdout
    assert "Context: prod" in result.stdout
    assert "Validation complete: 8/8 checks passed" in result.stdout
