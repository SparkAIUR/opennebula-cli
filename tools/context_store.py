"""Helper CLI for the internal context store."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from opennebula_cli.dev.context_store import ContextEntry, ContextStore

app = typer.Typer(no_args_is_help=True, help="Manage the private project context store.")


def store() -> ContextStore:
    """Return the default context store."""

    return ContextStore(Path("refs/docs/ctx/context.db"))


@app.command("init")
def init_store() -> None:
    """Initialize the SQLite schema."""

    instance = store()
    instance.init()
    typer.echo(instance.path)


@app.command("add")
def add_entry(
    kind: str,
    scope: str,
    title: str,
    summary: str,
    body: Annotated[str, typer.Option("--body")],
    source_path: Annotated[str | None, typer.Option("--source-path")] = None,
    source_ref: Annotated[str | None, typer.Option("--source-ref")] = None,
    status: Annotated[str, typer.Option("--status")] = "active",
    importance: Annotated[int, typer.Option("--importance")] = 3,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
) -> None:
    """Add a context entry."""

    instance = store()
    instance.init()
    entry_id = instance.add(
        ContextEntry(
            kind=kind,
            scope=scope,
            title=title,
            summary=summary,
            body=body,
            source_path=source_path,
            source_ref=source_ref,
            status=status,
            importance=importance,
        ),
        tags=tag or [],
    )
    typer.echo(entry_id)


@app.command("show")
def show_entry(entry_id: int) -> None:
    """Show a single entry."""

    instance = store()
    instance.init()
    row = instance.get(entry_id)
    if row is None:
        raise typer.Exit(1)
    for key in row.keys():
        typer.echo(f"{key}: {row[key]}")


@app.command("search")
def search_entries(query: str, limit: int = typer.Option(10, "--limit")) -> None:
    """Search the context store."""

    instance = store()
    instance.init()
    for row in instance.search(query, limit=limit):
        typer.echo(f"[{row['id']}] {row['title']} :: {row['summary']}")


@app.command("update")
def update_entry(
    entry_id: int,
    summary: str | None = typer.Option(None, "--summary"),
    body: str | None = typer.Option(None, "--body"),
) -> None:
    """Update an existing entry."""

    instance = store()
    instance.init()
    instance.update(entry_id, summary=summary, body=body)
    typer.echo(entry_id)


@app.command("prune")
def prune_entries(status: str = typer.Option("active", "--status")) -> None:
    """List entries by status for manual pruning."""

    instance = store()
    instance.init()
    for row in instance.list_entries(limit=500):
        if row["status"] == status:
            typer.echo(f"[{row['id']}] {row['title']}")


@app.command("export-md")
def export_markdown(output_path: Path = Path("refs/KB.md")) -> None:
    """Export a Markdown digest."""

    instance = store()
    instance.init()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(instance.export_markdown(), encoding="utf-8")
    typer.echo(output_path)


if __name__ == "__main__":
    app()
