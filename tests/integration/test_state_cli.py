from __future__ import annotations

import json
from pathlib import Path

import yaml

from opennebula_cli.cli.app import app
from opennebula_cli.sdk.models.system import ServerInfo
from opennebula_cli.state_store import StateStore


def test_state_ctx_set_and_use(runner, state_env: dict[str, str]) -> None:
    env = state_env
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

    get_result = runner.invoke(app, ["--output", "json", "state", "ctx", "get"], env=env)
    assert get_result.exit_code == 0
    assert json.loads(get_result.stdout)["name"] == "staging"
    assert json.loads(get_result.stdout)["active"] is True

    show_result = runner.invoke(
        app, ["--output", "json", "state", "ctx", "show", "staging"], env=env
    )
    assert show_result.exit_code == 0
    assert json.loads(show_result.stdout)["name"] == "staging"

    list_result = runner.invoke(app, ["--output", "json", "state", "ctx", "list"], env=env)
    assert list_result.exit_code == 0
    assert {item["name"] for item in json.loads(list_result.stdout)} == {
        "staging",
        "production",
    }

    list_auth_result = runner.invoke(app, ["state", "ctx", "list", "--source", "auth"], env=env)
    assert list_auth_result.exit_code == 0
    assert "production" in list_auth_result.stdout

    list_db_result = runner.invoke(app, ["state", "ctx", "list", "--source", "db"], env=env)
    assert list_db_result.exit_code == 0
    assert "No results." in list_db_result.stdout

    list_invalid = runner.invoke(app, ["state", "ctx", "list", "--source", "nope"], env=env)
    assert list_invalid.exit_code != 0
    assert "must be one of: auto, auth, db" in list_invalid.output


def test_state_lock_enable_blocks_command_then_disable(runner, state_env: dict[str, str]) -> None:
    env = state_env
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


def test_state_lock_and_context_actions_honor_machine_output(
    runner,
    state_env: dict[str, str],
) -> None:
    env = state_env
    enabled = runner.invoke(
        app,
        [
            "--output",
            "json",
            "state",
            "lock",
            "enable",
            "--actions",
            "show",
            "--commands",
            "vm",
        ],
        input="\n",
        env=env,
    )
    assert enabled.exit_code == 0
    assert json.loads(enabled.stdout) == {
        "actions": ["show"],
        "commands": ["vm"],
        "enabled": True,
        "password_set": False,
    }

    status = runner.invoke(app, ["--output", "json", "state", "lock", "status"], env=env)
    assert status.exit_code == 0
    assert json.loads(status.stdout)["enabled"] is True

    disabled = runner.invoke(
        app,
        ["--output", "json", "state", "lock", "disable", "--yes"],
        env=env,
    )
    assert disabled.exit_code == 0
    assert json.loads(disabled.stdout)["enabled"] is False

    context_set = runner.invoke(
        app,
        [
            "--output",
            "json",
            "state",
            "ctx",
            "set",
            "--name",
            "machine",
            "--endpoint",
            "https://machine.example.com/RPC2",
            "--user",
            "user",
            "--password",
            "pass",
        ],
        env=env,
    )
    assert context_set.exit_code == 0
    assert json.loads(context_set.stdout) == {
        "active": True,
        "name": "machine",
        "updated": True,
    }


def test_state_lock_enable_delete_without_commands_blocks_delete_across_commands(
    runner,
    state_env: dict[str, str],
) -> None:
    env = state_env
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


def test_state_ctx_use_missing_context_errors(runner, state_env: dict[str, str]) -> None:
    result = runner.invoke(app, ["state", "ctx", "use", "missing"], env=state_env)
    assert result.exit_code != 0
    assert "was not found in auth config" in result.output


def test_state_ctx_get_and_list_without_contexts(runner, state_env: dict[str, str]) -> None:
    env = state_env

    get_result = runner.invoke(app, ["--output", "json", "state", "ctx", "get"], env=env)
    assert get_result.exit_code == 0
    assert json.loads(get_result.stdout) is None

    list_result = runner.invoke(app, ["--output", "json", "state", "ctx", "list"], env=env)
    assert list_result.exit_code == 0
    assert json.loads(list_result.stdout) == []


def test_state_ctx_show_missing_context_errors(runner, state_env: dict[str, str]) -> None:
    env = state_env
    result = runner.invoke(app, ["state", "ctx", "show", "missing"], env=env)
    assert result.exit_code != 0
    assert "was not found in auth config" in result.output


def test_state_ctx_validate_checks_endpoints_and_prints_progress(
    runner,
    state_env: dict[str, str],
    monkeypatch,
) -> None:
    env = state_env
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
    monkeypatch.setattr(
        "opennebula_cli.sdk.client.OneClient.server_info",
        lambda _self: ServerInfo(
            version="7.4.0",
            profile="7.4",
            endpoint="http://on.sprkinfra.com:2633/RPC2",
            username="user1",
            transport="raw",
        ),
    )

    result = runner.invoke(
        app,
        ["--output", "json", "state", "ctx", "validate", "--timeout", "3"],
        env=env,
    )

    assert result.exit_code == 0
    checks = json.loads(result.stdout)
    assert {item["service"] for item in checks} == {"xmlrpc", "oneflow", "firestone", "web"}
    assert all(item["ok"] for item in checks)
    assert next(item for item in checks if item["service"] == "xmlrpc")["authenticated"] is True


def test_state_ctx_validate_all_contexts(
    runner,
    state_env: dict[str, str],
    monkeypatch,
) -> None:
    env = state_env
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
    monkeypatch.setattr(
        "opennebula_cli.sdk.client.OneClient.server_info",
        lambda self: ServerInfo(
            version="7.4.0",
            profile="7.4",
            endpoint=self.config.connection.endpoint,
            username=self.config.auth.username,
            transport="raw",
        ),
    )

    result = runner.invoke(app, ["--output", "json", "state", "ctx", "validate", "--all"], env=env)
    assert result.exit_code == 0
    checks = json.loads(result.stdout)
    assert {item["context"] for item in checks} == {"staging", "prod"}
    assert len(checks) == 8
    assert all(item["ok"] for item in checks)


def test_state_ctx_sync_copies_auth_config_to_state_db(runner, state_env: dict[str, str]) -> None:
    env = state_env

    auth_payload = {
        "current_context": "staging",
        "contexts": [
            {
                "name": "staging",
                "endpoint": "https://staging.example.com/RPC2",
                "version": "v7.0.2",
                "auth": {"username": "user1", "password": "pass1"},
            },
            {
                "name": "production",
                "endpoint": "https://prod.example.com/RPC2",
                "version": "v7.0.2",
                "auth": {"username": "user2", "password": "pass2"},
            },
        ],
    }
    auth_config = Path(env["OPENNEBULA_CLI_AUTH_CONFIG"])
    auth_config.parent.mkdir(parents=True, exist_ok=True)
    auth_config.write_text(yaml.safe_dump(auth_payload, sort_keys=False), encoding="utf-8")

    result = runner.invoke(app, ["state", "ctx", "sync"], env=env)
    assert result.exit_code == 0
    assert (
        "Synced 2 context(s) from auth config to state database. Active context: staging."
        in result.stdout
    )

    store = StateStore(path=Path(env["OPENNEBULA_CLI_STATE_DB"]))
    contexts = store.list_contexts()
    assert {item.name for item in contexts} == {"staging", "production"}
    assert store.active_context_name() == "staging"

    list_db = runner.invoke(
        app, ["--output", "json", "state", "ctx", "list", "--source", "db"], env=env
    )
    assert list_db.exit_code == 0
    listed = json.loads(list_db.stdout)
    assert {item["name"] for item in listed} == {"staging", "production"}
    assert next(item for item in listed if item["name"] == "staging")["active"] is True


def test_state_ctx_sync_requires_valid_auth_config(runner, state_env: dict[str, str]) -> None:
    env = state_env

    result = runner.invoke(app, ["state", "ctx", "sync"], env=env)
    assert result.exit_code != 0
    assert "Auth config was not found or is invalid" in result.output
