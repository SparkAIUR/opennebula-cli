from __future__ import annotations

from pathlib import Path

from opennebula_cli.auth.context_config import auth_config_path, load_auth_config


def test_auth_config_path_prefers_env(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "auth.yaml"
    monkeypatch.setenv("OPENNEBULA_CLI_AUTH_CONFIG", str(target))

    assert auth_config_path() == target


def test_load_auth_config_parses_current_context(tmp_path: Path, monkeypatch) -> None:
    auth_file = tmp_path / "auth.yaml"
    auth_file.write_text(
        """
current_context: staging
contexts:
  - name: staging
    endpoint: https://staging.example.com/RPC2
    version: v7.0.2
    endpoints:
      oneflow: https://staging.example.com:2474
      web: https://staging.example.com:9869
    config:
      oneflow_host: localhost
    auth:
      username: user1
      password: pass1
  - name: production
    endpoint: https://prod.example.com/RPC2
    auth:
      username: user2
      password: pass2
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENNEBULA_CLI_AUTH_CONFIG", str(auth_file))

    loaded = load_auth_config()
    assert loaded is not None
    assert loaded.current_context == "staging"
    current = loaded.resolve_current()
    assert current is not None
    assert current.endpoint == "https://staging.example.com/RPC2"
    assert current.auth.username == "user1"
    assert current.endpoints == {
        "oneflow": "https://staging.example.com:2474",
        "web": "https://staging.example.com:9869",
    }
    assert current.config == {"oneflow_host": "localhost"}


def test_load_auth_config_returns_none_for_invalid_shape(tmp_path: Path, monkeypatch) -> None:
    auth_file = tmp_path / "auth.yaml"
    auth_file.write_text("current_context: 1\ncontexts: nope\n", encoding="utf-8")
    monkeypatch.setenv("OPENNEBULA_CLI_AUTH_CONFIG", str(auth_file))

    assert load_auth_config() is None
