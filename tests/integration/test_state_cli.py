from __future__ import annotations

from pathlib import Path

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

    use_result = runner.invoke(app, ["state", "ctx", "use", "staging"], env=env)
    assert use_result.exit_code == 0
    assert "Context switched to 'staging'" in use_result.stdout

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


def test_state_ctx_use_missing_context_errors(tmp_path: Path) -> None:
    result = runner.invoke(app, ["state", "ctx", "use", "missing"], env=_env(tmp_path))
    assert result.exit_code != 0
    assert "was not found in state database" in result.output


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
    assert "was not found in state database" in result.output
