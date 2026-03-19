from __future__ import annotations

from pathlib import Path

from opennebula_cli.dev.context_store import ContextEntry, ContextStore


def test_context_store_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "context.db"
    store = ContextStore(db)
    store.init()
    entry_id = store.add(
        ContextEntry(
            kind="decision",
            scope="tests",
            title="Store works",
            summary="Round-trip coverage",
            body="Created during unit testing.",
        )
    )
    row = store.get(entry_id)
    assert row is not None
    assert row["title"] == "Store works"
    assert store.search("round*")[0]["id"] == entry_id
