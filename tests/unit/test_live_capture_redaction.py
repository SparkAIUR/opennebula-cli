from __future__ import annotations

from pathlib import Path

from opennebula_cli.dev.context_store import ContextStore
from opennebula_cli.dev.live_capture import (
    ensure_safe_command,
    import_capture_records,
    jsonl_load,
    redact_output,
)


def test_redact_output_masks_infra_and_secrets() -> None:
    payload = """
    {
      "endpoint": "https://opennebula.internal.example.com/RPC2",
      "token": "abc123",
      "ips": ["10.0.0.5"],
      "host": "node01.example.com",
      "mac": "aa:bb:cc:dd:ee:ff"
    }
    """
    redacted, count = redact_output(payload)
    assert "<redacted-url>" in redacted
    assert "<redacted-secret>" in redacted
    assert "<redacted-ipv4>" in redacted
    assert "<redacted-hostname>" in redacted or "<redacted-infra>" in redacted
    assert "<redacted-mac>" in redacted
    assert count >= 4


def test_ensure_safe_command_rejects_mutation() -> None:
    try:
        ensure_safe_command(("one", "vm", "delete", "10"))
    except ValueError as exc:
        assert "Unsafe" in str(exc)
    else:
        raise AssertionError("Mutating commands must be rejected.")


def test_import_capture_records_updates_context_store(tmp_path: Path) -> None:
    records = jsonl_load(
        "\n".join(
            [
                '{"record_type":"meta","timestamp":"20260318T010203Z","families":["vm"]}',
                (
                    '{"record_type":"command","timestamp":"20260318T010203Z","family":"vm",'
                    '"verb":"list","capture_kind":"data","command":"one vm list --output json",'
                    '"safe_readonly":true,"status":"ok","exit_code":0,"stdout_redacted":"[]",'
                    '"stderr_redacted":"","observed_ids":[],"redaction_count":0}'
                ),
                '{"record_type":"summary","timestamp":"20260318T010203Z"}',
            ]
        )
    )
    artifact_root = tmp_path / "artifacts"
    store_path = tmp_path / "context.db"
    kb_path = tmp_path / "KB.md"

    summary_path = import_capture_records(
        records,
        artifact_root=artifact_root,
        store_path=store_path,
        kb_path=kb_path,
    )

    store = ContextStore(store_path)
    row = store.search("vm*")[0]
    assert row["scope"] == "vm.list"
    assert summary_path.exists()
    assert kb_path.exists()
