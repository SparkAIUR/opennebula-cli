"""Generic polling waiters."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn

from opennebula_cli.sdk.exceptions import TimeoutError
from opennebula_cli.sdk.models.common import WaitResult, normalize_value

T = TypeVar("T")


def wait_for(
    *,
    resource: str,
    resource_id: int,
    fetch: Callable[[], T],
    predicate: Callable[[T], bool],
    state_label: Callable[[T], str],
    timeout: float,
    poll_interval: float,
    show_progress: bool,
) -> WaitResult:
    """Poll a resource until a predicate is satisfied."""

    deadline = time.monotonic() + timeout
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        transient=True,
    )
    task_id: TaskID | None = None
    context = progress if show_progress else None
    if context is not None:
        context.start()
        task_id = context.add_task(f"Waiting for {resource} {resource_id}", total=None)
    try:
        while True:
            item = fetch()
            state = state_label(item)
            if task_id is not None:
                progress.update(
                    task_id,
                    description=f"Waiting for {resource} {resource_id}: {state}",
                )
            if predicate(item):
                return WaitResult(
                    resource=resource,
                    id=resource_id,
                    state=state,
                    detail={"resource": normalize_value(item)},
                )
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Timed out waiting for {resource} {resource_id} to reach target state."
                )
            time.sleep(poll_interval)
    finally:
        if context is not None:
            context.stop()
