"""Import private read-only capture artifacts into local summaries and context DB."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from opennebula_cli.dev.live_capture import (
    DEFAULT_ARTIFACT_ROOT,
    DEFAULT_CONTEXT_DB,
    DEFAULT_KB_PATH,
    import_capture_records,
    jsonl_load,
)

app = typer.Typer(no_args_is_help=True, help="Import JSONL live capture records.")


@app.command("import")
def import_capture(
    input_path: Annotated[Path | None, typer.Option("--input")] = None,
    artifact_root: Annotated[Path, typer.Option("--artifact-root")] = DEFAULT_ARTIFACT_ROOT,
    store_path: Annotated[Path, typer.Option("--store-path")] = DEFAULT_CONTEXT_DB,
    kb_path: Annotated[Path, typer.Option("--kb-path")] = DEFAULT_KB_PATH,
) -> None:
    """Read JSONL capture data and update the local private knowledge artifacts."""

    payload = input_path.read_text(encoding="utf-8") if input_path is not None else sys.stdin.read()
    records = jsonl_load(payload)
    summary_path = import_capture_records(
        records,
        artifact_root=artifact_root,
        store_path=store_path,
        kb_path=kb_path,
    )
    typer.echo(summary_path)


if __name__ == "__main__":
    app()
