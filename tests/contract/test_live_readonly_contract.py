from __future__ import annotations

import json
from pathlib import Path

import pytest

from opennebula_cli.dev.live_capture import jsonl_load


def latest_capture() -> Path | None:
    root = Path("refs/tasks/live-capture")
    if not root.exists():
        return None
    captures = sorted(root.glob("*/capture.jsonl"))
    return captures[-1] if captures else None


@pytest.mark.contract
def test_live_capture_contract_fields() -> None:
    capture_path = latest_capture()
    if capture_path is None:
        pytest.skip("No private live capture artifact is available.")
    records = jsonl_load(capture_path.read_text(encoding="utf-8"))
    command_records = [record for record in records if record.get("record_type") == "command"]
    assert command_records
    for record in command_records:
        assert "family" in record
        assert "verb" in record
        assert "status" in record
        assert "safe_readonly" in record
        assert record.get("capture_kind") in {"help", "data", "official-help"}
        assert isinstance(record.get("redaction_count"), int)
        if record.get("capture_kind") == "data" and record.get("status") == "ok":
            json.loads(str(record.get("stdout_redacted", "")))
