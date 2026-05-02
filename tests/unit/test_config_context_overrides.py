from __future__ import annotations

from pathlib import Path

from opennebula_cli.config.merge import merge_runtime_config
from opennebula_cli.config.models import ProfileConfig
from opennebula_cli.state_store import StateStore, StoredContext


def _base_merge() -> dict[str, object]:
    return {
        "profile_name": None,
        "profile": ProfileConfig(),
        "cli_endpoint": None,
        "cli_auth": None,
        "cli_user": None,
        "cli_password": None,
        "cli_output": "table",
        "cli_no_pager": False,
        "cli_timeout": None,
        "cli_no_verify": False,
        "cli_cert_dir": None,
        "verbose": 0,
        "debug": False,
    }


def test_auth_yaml_overrides_one_env(monkeypatch, tmp_path: Path) -> None:
    auth_file = tmp_path / "auth.yaml"
    auth_file.write_text(
        """
current_context: staging
contexts:
  - name: staging
    endpoint: https://staging.example.com/RPC2
    endpoints:
      oneflow: https://staging-flow.example.com:2474
    config:
      oneflow_host: localhost
    auth:
      username: file-user
      password: file-pass
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENNEBULA_CLI_AUTH_CONFIG", str(auth_file))
    monkeypatch.setenv("ONE_XMLRPC", "https://env.example.com/RPC2")
    monkeypatch.setenv("ONE_AUTH", "literal:env-user:env-pass")

    resolved = merge_runtime_config(**_base_merge())

    assert resolved.connection.endpoint == "https://staging.example.com/RPC2"
    assert resolved.auth.username == "file-user"
    assert resolved.auth.secret == "file-pass"
    assert resolved.auth.source == "auth-config:staging"
    assert resolved.connection.service_endpoints["oneflow"] == "https://staging-flow.example.com:2474"
    assert resolved.connection.service_endpoints["firestone"] == "https://staging.example.com:2616"
    assert resolved.connection.service_endpoints["web"] == "https://staging.example.com:9869"
    assert resolved.connection.service_config == {"oneflow_host": "localhost"}


def test_cli_auth_and_endpoint_override_context(monkeypatch, tmp_path: Path) -> None:
    auth_file = tmp_path / "auth.yaml"
    auth_file.write_text(
        """
current_context: staging
contexts:
  - name: staging
    endpoint: https://staging.example.com/RPC2
    auth:
      username: file-user
      password: file-pass
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENNEBULA_CLI_AUTH_CONFIG", str(auth_file))

    kwargs = _base_merge()
    kwargs["cli_endpoint"] = "https://cli.example.com/RPC2"
    kwargs["cli_auth"] = "literal:cli-user:cli-pass"
    resolved = merge_runtime_config(**kwargs)

    assert resolved.connection.endpoint == "https://cli.example.com/RPC2"
    assert resolved.auth.username == "cli-user"
    assert resolved.auth.secret == "cli-pass"
    assert resolved.connection.service_endpoints["oneflow"] == "https://cli.example.com:2474"


def test_state_context_used_when_auth_yaml_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENNEBULA_CLI_AUTH_CONFIG", raising=False)
    monkeypatch.delenv("ONE_XMLRPC", raising=False)
    monkeypatch.delenv("ONE_AUTH", raising=False)
    monkeypatch.setenv("OPENNEBULA_CLI_STATE_DB", str(tmp_path / "state.db"))

    store = StateStore()
    store.upsert_context(
        StoredContext(
            name="dev",
            endpoint="https://dev.example.com/RPC2",
            username="dev-user",
            password="dev-pass",
            version="v7.0.2",
        )
    )

    resolved = merge_runtime_config(**_base_merge())

    assert resolved.connection.endpoint == "https://dev.example.com/RPC2"
    assert resolved.auth.username == "dev-user"
    assert resolved.auth.secret == "dev-pass"
    assert resolved.auth.source == "state-context:dev"
    assert resolved.connection.service_endpoints["oneflow"] == "https://dev.example.com:2474"
    assert resolved.connection.service_endpoints["firestone"] == "https://dev.example.com:2616"
    assert resolved.connection.service_endpoints["web"] == "https://dev.example.com:9869"
