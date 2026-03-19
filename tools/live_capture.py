"""CLI wrapper for the read-only live capture helper."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from opennebula_cli.dev.live_capture import (
    DEFAULT_ARTIFACT_ROOT,
    capture_all,
    jsonl_dump,
    write_capture_artifact,
)

app = typer.Typer(no_args_is_help=True, help="Capture safe read-only OpenNebula observations.")


@app.command("capture")
def capture(
    family: Annotated[list[str] | None, typer.Option("--family")] = None,
    write_artifact: Annotated[bool, typer.Option("--write-artifact")] = False,
    artifact_root: Annotated[Path, typer.Option("--artifact-root")] = DEFAULT_ARTIFACT_ROOT,
) -> None:
    """Execute the safe capture plan and emit JSONL to stdout."""

    repo_root = Path(__file__).resolve().parent.parent
    records = capture_all(repo_root=repo_root, families=family)
    output = jsonl_dump(records)
    typer.echo(output, nl=False)
    if write_artifact:
        path = write_capture_artifact(records, artifact_root=artifact_root)
        typer.echo(str(path), err=True)


if __name__ == "__main__":
    app()
