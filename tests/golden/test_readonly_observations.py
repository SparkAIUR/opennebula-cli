from __future__ import annotations

import json
from pathlib import Path

import pytest


def latest_summary() -> Path | None:
    root = Path("refs/tasks/live-capture")
    if not root.exists():
        return None
    summaries = sorted(root.glob("*/summary.json"))
    return summaries[-1] if summaries else None


@pytest.mark.golden
def test_live_summary_shape() -> None:
    summary_path = latest_summary()
    if summary_path is None:
        pytest.skip("No private live summary artifact is available.")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "captured_at" in summary
    assert isinstance(summary.get("commands"), list)
    assert "families" in summary
    assert "ok_commands" in summary
