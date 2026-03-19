"""Read-only live capture helpers for private OpenNebula observation."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from opennebula_cli.dev.context_store import ContextEntry, ContextStore

READ_ONLY_FAMILIES: tuple[str, ...] = (
    "vm",
    "host",
    "image",
    "template",
    "vnet",
    "datastore",
    "cluster",
)

IMPLEMENTED_COMMANDS: dict[str, tuple[str, ...]] = {
    "vm": ("list", "show", "poweroff"),
    "host": ("list", "show", "flush"),
    "image": ("list", "show", "delete"),
    "template": ("list", "show", "delete", "instantiate"),
    "vnet": ("list", "show"),
    "datastore": ("list", "show"),
    "cluster": ("list", "show"),
}

DEFAULT_ARTIFACT_ROOT = Path("refs/tasks/live-capture")
DEFAULT_CONTEXT_DB = Path("refs/docs/ctx/context.db")
DEFAULT_KB_PATH = Path("refs/KB.md")

SECRET_KEY_TOKENS = ("password", "secret", "token", "session", "auth", "ssh_key", "key")
INFRA_KEY_TOKENS = ("endpoint", "hostname", "host", "bridge", "server", "ip", "mac", "address")
URL_PATTERN = re.compile(r"https?://[^\s\"'>]+")
IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_PATTERN = re.compile(r"\b(?:[0-9A-Fa-f]{0,4}:){2,}[0-9A-Fa-f]{0,4}\b")
MAC_PATTERN = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
HOSTNAME_PATTERN = re.compile(r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")


@dataclass(slots=True, frozen=True)
class CaptureCommand:
    """Single safe command capture request."""

    family: str
    verb: str
    argv: tuple[str, ...]
    capture_kind: Literal["help", "data", "official-help"]
    safe_readonly: bool = True
    use_uv: bool = True


@dataclass(slots=True, frozen=True)
class CommandRecord:
    """Structured command capture output."""

    record_type: Literal["command"]
    family: str
    verb: str
    capture_kind: Literal["help", "data", "official-help"]
    command: str
    safe_readonly: bool
    status: str
    exit_code: int
    stdout_redacted: str
    stderr_redacted: str
    observed_ids: list[int]
    redaction_count: int
    timestamp: str


def timestamp_now() -> str:
    """Return a compact UTC timestamp for artifact naming."""

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def compatibility_script(family: str) -> str:
    """Return the compat executable name for a family."""

    return f"one{family}"


def validate_requested_families(families: Sequence[str] | None) -> list[str]:
    """Validate and normalize requested family filters."""

    if not families:
        return list(READ_ONLY_FAMILIES)
    normalized = [family.strip() for family in families if family.strip()]
    invalid = sorted(set(normalized).difference(READ_ONLY_FAMILIES))
    if invalid:
        raise ValueError(f"Unsupported read-only family selection: {', '.join(invalid)}")
    return normalized


def ensure_safe_command(argv: Sequence[str]) -> None:
    """Reject commands outside the hard-coded read-only allowlist."""

    if not argv:
        raise ValueError("Command cannot be empty.")
    first = Path(argv[0]).name
    if first == "one":
        _validate_canonical_command(argv)
        return
    if first in {compatibility_script(family) for family in READ_ONLY_FAMILIES}:
        _validate_compat_command(argv)
        return
    raise ValueError(f"Unsafe command rejected: {' '.join(argv)}")


def _validate_canonical_command(argv: Sequence[str]) -> None:
    if len(argv) < 3:
        raise ValueError(f"Incomplete canonical command: {' '.join(argv)}")
    family = argv[1]
    if family not in IMPLEMENTED_COMMANDS:
        raise ValueError(f"Unsupported family: {family}")
    if len(argv) == 3 and argv[2] == "--help":
        return
    if len(argv) == 4 and argv[3] == "--help" and argv[2] in IMPLEMENTED_COMMANDS[family]:
        return
    if len(argv) == 5 and list(argv[2:]) == ["list", "--output", "json"]:
        return
    if (
        len(argv) == 6
        and argv[2] == "show"
        and _is_int_like(argv[3])
        and argv[4] == "--output"
        and argv[5] == "json"
    ):
        return
    raise ValueError(f"Unsafe canonical command rejected: {' '.join(argv)}")


def _validate_compat_command(argv: Sequence[str]) -> None:
    command_name = argv[0]
    family = command_name[3:]
    if family not in IMPLEMENTED_COMMANDS:
        raise ValueError(f"Unsupported compatibility command: {command_name}")
    if len(argv) == 2 and argv[1] == "--help":
        return
    if len(argv) == 3 and argv[2] == "--help" and argv[1] in IMPLEMENTED_COMMANDS[family]:
        return
    raise ValueError(f"Unsafe compatibility command rejected: {' '.join(argv)}")


def _is_int_like(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def build_help_commands(family: str) -> list[CaptureCommand]:
    """Build the static help capture sequence for a family."""

    compat = compatibility_script(family)
    commands = [
        CaptureCommand(family, "__family__", ("one", family, "--help"), "help"),
        CaptureCommand(family, "__family__", (compat, "--help"), "help"),
    ]
    for verb in IMPLEMENTED_COMMANDS[family]:
        commands.append(CaptureCommand(family, verb, ("one", family, verb, "--help"), "help"))
        commands.append(CaptureCommand(family, verb, (compat, verb, "--help"), "help"))
    return commands


def external_official_help_commands(
    repo_root: Path, families: Sequence[str]
) -> list[CaptureCommand]:
    """Return help commands for externally installed official CLIs when available."""

    commands: list[CaptureCommand] = []
    for family in families:
        binary = compatibility_script(family)
        path = _external_binary_path(binary, repo_root)
        if path is None:
            continue
        commands.append(
            CaptureCommand(
                family=family,
                verb="__official__",
                argv=(path.as_posix(), "--help"),
                capture_kind="official-help",
                use_uv=False,
            )
        )
    return commands


def _external_binary_path(binary: str, repo_root: Path) -> Path | None:
    path = shutil.which(binary)
    if path is None:
        return None
    resolved = Path(path).resolve()
    repo_resolved = repo_root.resolve()
    if repo_resolved in resolved.parents:
        return None
    if ".venv" in resolved.parts:
        return None
    return resolved


def capture_all(
    *,
    repo_root: Path,
    families: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    """Capture all safe read-only observations for the selected families."""

    selected_families = validate_requested_families(families)
    timestamp = timestamp_now()
    records: list[dict[str, object]] = [
        {
            "record_type": "meta",
            "timestamp": timestamp,
            "families": selected_families,
            "cwd": str(repo_root),
        }
    ]
    executed = 0
    skipped = 0
    for family in selected_families:
        for command in build_help_commands(family):
            records.append(
                asdict(capture_command(command, repo_root=repo_root, timestamp=timestamp))
            )
            executed += 1
        list_command = CaptureCommand(
            family=family,
            verb="list",
            argv=("one", family, "list", "--output", "json"),
            capture_kind="data",
        )
        list_record = capture_command(list_command, repo_root=repo_root, timestamp=timestamp)
        records.append(asdict(list_record))
        executed += 1
        first_id = list_record.observed_ids[0] if list_record.observed_ids else None
        if first_id is None:
            skipped += 1
            records.append(
                asdict(
                    CommandRecord(
                        record_type="command",
                        family=family,
                        verb="show",
                        capture_kind="data",
                        command=f"one {family} show <id> --output json",
                        safe_readonly=True,
                        status="skipped_no_resources",
                        exit_code=0,
                        stdout_redacted="",
                        stderr_redacted="",
                        observed_ids=[],
                        redaction_count=0,
                        timestamp=timestamp,
                    )
                )
            )
            continue
        show_command = CaptureCommand(
            family=family,
            verb="show",
            argv=("one", family, "show", str(first_id), "--output", "json"),
            capture_kind="data",
        )
        records.append(
            asdict(capture_command(show_command, repo_root=repo_root, timestamp=timestamp))
        )
        executed += 1
    for command in external_official_help_commands(repo_root, selected_families):
        records.append(asdict(capture_command(command, repo_root=repo_root, timestamp=timestamp)))
        executed += 1
    records.append(
        {
            "record_type": "summary",
            "timestamp": timestamp,
            "families": selected_families,
            "executed_commands": executed,
            "skipped_commands": skipped,
        }
    )
    return records


def capture_command(command: CaptureCommand, *, repo_root: Path, timestamp: str) -> CommandRecord:
    """Execute and redact a single safe command."""

    ensure_safe_command(command.argv)
    completed = subprocess.run(
        _run_argv(command),
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
        env=_safe_env(os.environ),
    )
    stdout_redacted, stdout_count = redact_output(completed.stdout)
    stderr_redacted, stderr_count = redact_output(completed.stderr)
    observed_ids = []
    if command.capture_kind == "data" and completed.returncode == 0:
        observed_ids = collect_observed_ids(stdout_redacted)
    return CommandRecord(
        record_type="command",
        family=command.family,
        verb=command.verb,
        capture_kind=command.capture_kind,
        command=" ".join(command.argv),
        safe_readonly=command.safe_readonly,
        status="ok" if completed.returncode == 0 else "command_failed",
        exit_code=completed.returncode,
        stdout_redacted=stdout_redacted,
        stderr_redacted=stderr_redacted,
        observed_ids=observed_ids,
        redaction_count=stdout_count + stderr_count,
        timestamp=timestamp,
    )


def _safe_env(source: Mapping[str, str]) -> dict[str, str]:
    env = dict(source)
    env.pop("ONE_AUTH", None)
    return env


def _run_argv(command: CaptureCommand) -> list[str]:
    if command.use_uv:
        return ["uv", "run", *command.argv]
    return list(command.argv)


def collect_observed_ids(text: str) -> list[int]:
    """Extract stable integer IDs from JSON output."""

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    ids: list[int] = []
    _walk_ids(payload, ids)
    return ids


def _walk_ids(payload: object, result: list[int]) -> None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if key == "id" and isinstance(value, int):
                result.append(value)
            else:
                _walk_ids(value, result)
        return
    if isinstance(payload, list):
        for item in payload:
            _walk_ids(item, result)


def redact_output(text: str) -> tuple[str, int]:
    """Redact structured JSON or plain text output."""

    if not text:
        return "", 0
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return redact_text(text)
    redacted_payload, count = redact_object(payload)
    return json.dumps(redacted_payload, indent=2, sort_keys=True), count


def redact_object(payload: object, *, parent_key: str | None = None) -> tuple[object, int]:
    """Recursively redact structured payloads."""

    if isinstance(payload, Mapping):
        result: dict[str, object] = {}
        count = 0
        for key, value in payload.items():
            lowered = key.lower()
            if any(token in lowered for token in SECRET_KEY_TOKENS):
                result[str(key)] = "<redacted-secret>"
                count += 1
                continue
            redacted_value, nested_count = redact_object(value, parent_key=lowered)
            result[str(key)] = redacted_value
            count += nested_count
        return result, count
    if isinstance(payload, list):
        items: list[object] = []
        count = 0
        for item in payload:
            redacted_item, nested_count = redact_object(item, parent_key=parent_key)
            items.append(redacted_item)
            count += nested_count
        return items, count
    if isinstance(payload, str):
        if parent_key and any(token in parent_key for token in SECRET_KEY_TOKENS):
            return "<redacted-secret>", 1
        if parent_key and any(token in parent_key for token in INFRA_KEY_TOKENS):
            redacted_text, count = redact_text(payload)
            if count == 0:
                return "<redacted-infra>", 1
            return redacted_text, count
        return redact_text(payload)
    return payload, 0


def redact_text(text: str) -> tuple[str, int]:
    """Redact plain text using stable pattern substitutions."""

    redacted = text
    count = 0
    for pattern, replacement in (
        (URL_PATTERN, "<redacted-url>"),
        (MAC_PATTERN, "<redacted-mac>"),
        (IPV4_PATTERN, "<redacted-ipv4>"),
        (IPV6_PATTERN, "<redacted-ipv6>"),
        (HOSTNAME_PATTERN, "<redacted-hostname>"),
    ):
        redacted, substitutions = pattern.subn(replacement, redacted)
        count += substitutions
    return redacted, count


def jsonl_dump(records: Sequence[Mapping[str, object]]) -> str:
    """Serialize records to JSONL."""

    return "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)


def jsonl_load(text: str) -> list[dict[str, object]]:
    """Parse JSONL into a list of dictionaries."""

    records: list[dict[str, object]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError("JSONL records must be objects.")
        records.append({str(key): value for key, value in parsed.items()})
    return records


def write_capture_artifact(
    records: Sequence[Mapping[str, object]],
    *,
    artifact_root: Path,
    timestamp: str | None = None,
) -> Path:
    """Write JSONL capture output to the private artifact tree."""

    selected_timestamp = timestamp or extract_timestamp(records)
    artifact_dir = artifact_root / selected_timestamp
    artifact_dir.mkdir(parents=True, exist_ok=True)
    capture_path = artifact_dir / "capture.jsonl"
    capture_path.write_text(jsonl_dump(records), encoding="utf-8")
    return capture_path


def extract_timestamp(records: Sequence[Mapping[str, object]]) -> str:
    """Extract the capture timestamp from record sets."""

    for record in records:
        timestamp = record.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            return timestamp
    return timestamp_now()


def import_capture_records(
    records: Sequence[Mapping[str, object]],
    *,
    artifact_root: Path,
    store_path: Path,
    kb_path: Path | None = None,
) -> Path:
    """Persist private summaries and context-store entries from a capture."""

    timestamp = extract_timestamp(records)
    artifact_dir = artifact_root / timestamp
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = artifact_dir / "summary.json"
    summary = build_summary(records)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    store = ContextStore(store_path)
    store.init()
    for record in records:
        if record.get("record_type") != "command":
            continue
        if record.get("capture_kind") != "data":
            continue
        family = record.get("family")
        verb = record.get("verb")
        status = record.get("status")
        if not isinstance(family, str) or not isinstance(verb, str) or not isinstance(status, str):
            continue
        store.add(
            ContextEntry(
                kind="live-observation",
                scope=f"{family}.{verb}",
                title=f"Live observation {family}.{verb}",
                summary=f"Read-only capture recorded {family}.{verb} with status {status}.",
                body=_build_observation_body(record),
                source_path=str(summary_path),
                source_ref=timestamp,
                status="observed" if status == "ok" else "skipped",
                importance=4 if status == "ok" else 2,
            ),
            tags=["live", "readonly", family, verb],
        )
    if kb_path is not None:
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        kb_path.write_text(store.export_markdown(), encoding="utf-8")
    return summary_path


def build_summary(records: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Aggregate capture records into a normalized summary."""

    summary: dict[str, object] = {
        "captured_at": extract_timestamp(records),
        "commands": [],
    }
    commands: list[dict[str, object]] = []
    for record in records:
        if record.get("record_type") != "command":
            continue
        commands.append(
            {
                "family": record.get("family"),
                "verb": record.get("verb"),
                "capture_kind": record.get("capture_kind"),
                "status": record.get("status"),
                "exit_code": record.get("exit_code"),
                "observed_ids": record.get("observed_ids"),
                "redaction_count": record.get("redaction_count"),
            }
        )
    summary["commands"] = commands
    summary["families"] = sorted(
        {
            str(command["family"])
            for command in commands
            if isinstance(command.get("family"), str) and command.get("family")
        }
    )
    summary["ok_commands"] = sum(1 for command in commands if command.get("status") == "ok")
    summary["skipped_commands"] = sum(
        1 for command in commands if command.get("status") == "skipped_no_resources"
    )
    return summary


def _build_observation_body(record: Mapping[str, object]) -> str:
    observed_ids = record.get("observed_ids")
    return "\n".join(
        [
            f"Command: {record.get('command', '')}",
            f"Status: {record.get('status', '')}",
            f"Exit code: {record.get('exit_code', '')}",
            f"Observed IDs: {observed_ids if isinstance(observed_ids, list) else []}",
            f"Redactions: {record.get('redaction_count', 0)}",
        ]
    )
